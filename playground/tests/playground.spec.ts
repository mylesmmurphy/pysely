import { expect, test } from "@playwright/test";

const prefix = `from typing import cast
from pysely.dialect import Dialect
from database import Database

dialect = cast(Dialect, globals()["dialect"])
db = Database(dialect=dialect)
`;

async function replaceQuery(page: import("@playwright/test").Page, code: string) {
  const editor = page.locator("#playground-query textarea");
  await editor.focus();
  await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
  await page.keyboard.insertText(code);
  return editor;
}

test("uses Pyright for table and joined-column suggestions", async ({ page }) => {
  await page.goto("/playground/");
  await expect(page.locator("#playground-intelligence-status")).toContainText("suggestions ready");

  await replaceQuery(page, `${prefix}db.select_from("")`);
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.insertText("p");
  const suggestions = page.locator(".suggest-widget.visible .label-name");
  await expect(suggestions).toContainText(["person", "pet"]);

  await page.keyboard.press("Escape");
  await replaceQuery(page, `${prefix}query = db.select_from("person")
joined = query.inner_join("pet", "person.id", "pet.owner_id")
joined.where("")`);
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.insertText("s");
  await expect(page.locator(".suggest-widget.visible")).toContainText("species");
  await expect(page.locator(".suggest-widget.visible")).toContainText("pet.species");

  await page.keyboard.press("Escape");
  await replaceQuery(page, `${prefix}query = db.select_from("person")
joined = query.inner_join("pet", "person.id", "pet.owner_id")
selected = joined.select("first_name").select_as("pet.name", "pet_name")

async def inspect() -> None:
    row = await selected.execute_take_first_or_throw()
    row[""]`);
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("Control+Space");
  await expect(page.locator(".suggest-widget.visible")).toContainText("pet_name");
  await expect(page.locator(".suggest-widget.visible")).toContainText("first_name");
});

test("scrolls editors and passes wheel scrolling to the page at the boundary", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/playground/");
  await expect(page.locator("#playground-query textarea")).toBeVisible();
  await replaceQuery(page, "# scroll\n".repeat(100));
  await page.evaluate(() => {
    const editor = (window as any).monaco.editor.getEditors().find(
      (editor: any) => editor.getModel()?.uri.path === "/workspace/query.py",
    );
    editor.setScrollTop(0);
    window.scrollTo(0, 0);
  });
  const bounds = (await page.locator("#playground-query").boundingBox())!;
  expect(bounds.y + bounds.height).toBeLessThan(900);
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
  const scrollTop = () => page.evaluate(() => (window as any).monaco.editor.getEditors().find(
    (editor: any) => editor.getModel()?.uri.path === "/workspace/query.py",
  ).getScrollTop());
  await page.mouse.wheel(0, 250);
  await expect.poll(scrollTop).toBeGreaterThan(0);
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  await page.mouse.wheel(0, -250);
  await expect.poll(scrollTop).toBe(0);
  await page.evaluate(() => {
    const editor = (window as any).monaco.editor.getEditors().find(
      (editor: any) => editor.getModel()?.uri.path === "/workspace/query.py",
    );
    editor.setScrollTop(editor.getScrollHeight());
  });
  await expect.poll(scrollTop).toBeGreaterThan(1000);
  await page.mouse.wheel(0, 500);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
});

test("keeps real execution available", async ({ page }) => {
  await page.goto("/playground/");
  await expect(page.locator("main h1")).not.toBeVisible();
  const header = await page.locator(".md-header").boundingBox();
  const playground = await page.locator("#playground-workbench").boundingBox();
  const gap = playground!.y - (header!.y + header!.height);
  expect(gap).toBeGreaterThanOrEqual(8);
  expect(gap).toBeLessThanOrEqual(20);
  await expect(page.locator("#playground-status")).toHaveText("Compiled", { timeout: 40_000 });
  await expect(page.locator("#playground-sql")).toContainText(
    'select "first_name", "pet"."name" as "pet_name"',
  );
  const query = await page.evaluate(() => {
    const monaco = (window as any).monaco;
    return monaco.editor.getModel(monaco.Uri.parse("file:///workspace/query.py")).getValue();
  });
  expect(query).toContain("results = await query.execute()");
  expect(query).toContain('result["pet_name"]');
});

test("preserves stock Pyright diagnostics for an invalid join", async ({ page }) => {
  await page.goto("/playground/");
  await expect(page.locator("#playground-intelligence-status")).toContainText("suggestions ready");
  await page.evaluate(code => {
    const monaco = (window as any).monaco;
    monaco.editor.getModel(monaco.Uri.parse("file:///workspace/query.py")).setValue(code);
  }, `${prefix}compiled = (
    db.select_from("person")
    .inner_join("pett", "owner_id", "person.id")
    .where("first_name", "=", "Jennifer")
    .select("first_name")
    .compile()
)`);
  const markers = () => page.evaluate(() => {
    const monaco = (window as any).monaco;
    return monaco.editor.getModelMarkers({}).filter((item: any) => item.resource.path === "/workspace/query.py")
      .map((item: any) => ({ code: item.code, start: item.startLineNumber, end: item.endLineNumber, owner: item.owner }));
  });
  await expect.poll(markers).toEqual(expect.arrayContaining([
    expect.objectContaining({ code: "reportArgumentType" }),
  ]));
  const result = await markers();
  expect(result.some((item: any) => item.code === "reportCallIssue")).toBe(true);
  expect(result.some((item: any) => item.code === "reportUnknownMemberType")).toBe(true);
  expect(result.some((item: any) => item.owner === "pysely")).toBe(false);
});

test("uses Pyright's argument range for an invalid parameter", async ({ page }) => {
  await page.goto("/playground/");
  await expect(page.locator("#playground-intelligence-status")).toContainText("suggestions ready");
  await page.evaluate(code => {
    const monaco = (window as any).monaco;
    monaco.editor.getModel(monaco.Uri.parse("file:///workspace/query.py")).setValue(code);
  }, `${prefix}compiled = (
    db.select_from("person")
    .where("first_namee", "=", "Jennifer")
    .select("first_name")
    .compile()
)`);
  const markers = () => page.evaluate(() => {
    const monaco = (window as any).monaco;
    return monaco.editor.getModelMarkers({}).filter((item: any) => item.resource.path === "/workspace/query.py")
      .map((item: any) => ({ code: item.code, start: item.startLineNumber, end: item.endLineNumber, owner: item.owner }));
  });
  await expect.poll(markers).toEqual([
    expect.objectContaining({ code: "reportArgumentType", owner: "pyright" }),
  ]);
  const [marker] = await markers();
  expect(marker.start).toBe(marker.end);
});
