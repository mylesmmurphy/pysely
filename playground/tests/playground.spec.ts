import { expect, test } from "@playwright/test";

const prefix = `from typing import cast
from pysely import Pysely
from pysely.dialect import Dialect
from database import DatabaseSchema

dialect = cast(Dialect, globals()["dialect"])
db = Pysely.create(schema=DatabaseSchema, dialect=dialect)
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
  await expect(page.locator(".suggest-widget.visible")).toContainText("status");

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

test("uses schema value types for where", async ({ page }) => {
  await page.goto("/playground/");
  await expect(page.locator("#playground-intelligence-status")).toContainText("suggestions ready");

  await replaceQuery(page, `${prefix}query = db.select_from("person")
query.where("person.status", "!=", "")`);
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("Control+Space");
  const suggestions = page.locator(".suggest-widget.visible");
  await expect(suggestions).toContainText("active");
  await expect(suggestions).toContainText("inactive");

  await page.keyboard.press("Escape");
  await replaceQuery(page, `${prefix}query = db.select_from("person")
query.where("person.status", "!=", "")`);
  const markers = () => page.evaluate(() => {
    const monaco = (window as any).monaco;
    return monaco.editor.getModelMarkers({}).filter(
      (item: any) => item.resource.path === "/workspace/query.py",
    );
  });
  await expect.poll(markers).toEqual(expect.arrayContaining([
    expect.objectContaining({ code: "reportArgumentType", owner: "pyright" }),
  ]));
});

test("hands scrolling to the page on the next gesture at the editor boundary", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/playground/");
  await expect(page.locator("#playground-query .monaco-editor")).toBeVisible();
  await replaceQuery(page, "# scroll\n".repeat(100));
  await page.evaluate(() => {
    const editor = (window as any).monaco.editor.getEditors().find(
      (editor: any) => editor.getModel()?.uri.path === "/workspace/query.py",
    );
    editor.setScrollTop(0);
    window.scrollTo(0, 0);
  });
  const bounds = (await page.locator("#playground-query").boundingBox())!;
  const parameters = (await page.locator(".pysely-playground__parameters").boundingBox())!;
  expect(parameters.y + parameters.height).toBeLessThanOrEqual(884);
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
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  await page.mouse.wheel(0, 400);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(50);
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
    'select "first_name", "last_name", "pet"."name" as "pet_name"',
  );
  await expect(page.locator(".pysely-playground__parameters")).toContainText(
    '["dog","active"]',
  );
  const query = await page.evaluate(() => {
    const monaco = (window as any).monaco;
    return monaco.editor.getModel(monaco.Uri.parse("file:///workspace/query.py")).getValue();
  });
  expect(query).toContain("rows = await query.execute()");
  expect(query).toContain('rows[0]["pet_name"]');
  expect(query).toContain('rows[0]["last_name"]');
});

test("labels playground navigation as an interactive editor", async ({ page }) => {
  await page.goto("/ROADMAP/");
  const link = page.locator('.pysely-page-nav a[href$="/playground/"]');
  await expect(link).toContainText("Open playground editor");
  await expect(link).toContainText("↗");
  await expect(link).toHaveClass(/md-button--primary/);
});

test("serves content-hashed documentation assets", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('link[href*="/assets/site."]')).toHaveAttribute("href", /site\.[a-f0-9]{12}\.css$/);
  await expect(page.locator('link[href*="/assets/playground."]')).toHaveAttribute("href", /playground\.[a-f0-9]{12}\.css$/);
  await expect(page.locator('script[src*="/assets/site."]')).toHaveAttribute("src", /site\.[a-f0-9]{12}\.js$/);
  await expect(page.locator('script[src*="/assets/playground."]')).toHaveAttribute("src", /playground\.[a-f0-9]{12}\.js$/);
});

test("separates playground at the bottom of the docs navigation", async ({ page }) => {
  await page.goto("/queries/");
  const items = page.locator('.md-nav--primary > .md-nav__list > .md-nav__item');
  const playground = items.last();
  await expect(playground).toContainText("Playground ↗");
  expect(await playground.evaluate(item => getComputedStyle(item).borderTopStyle)).toBe("solid");
});

test("reloads styled Monaco after leaving the playground", async ({ page }) => {
  let playgroundLoads = 0;
  page.on("request", request => {
    if (new URL(request.url()).pathname === "/playground/" && request.isNavigationRequest()) playgroundLoads += 1;
  });
  await page.goto("/playground/");
  await expect(page.locator("#playground-query .monaco-editor")).toBeVisible();
  await page.getByRole("link", { name: "Pysely", exact: true }).first().click();
  await expect(page).toHaveURL(/\/$/);
  await page.getByRole("link", { name: /Open interactive editor/ }).click();
  const editor = page.locator("#playground-query .monaco-editor");
  await expect(editor).toBeVisible();
  await expect(editor).toHaveCSS("position", "relative");
  await expect(editor.locator("textarea.inputarea")).toHaveCSS("position", "absolute");
  await expect.poll(() => playgroundLoads).toBe(2);
  await expect(page.locator("#playground-status")).toHaveText("Compiled", { timeout: 40_000 });
});

test("restores styled Monaco through docs and browser history", async ({ page }) => {
  await page.goto("/playground/");
  const editor = page.locator("#playground-query .monaco-editor");
  await expect(editor).toBeVisible();
  await expect(editor).toHaveCSS("position", "relative");

  await page.getByRole("link", { name: "Pysely", exact: true }).first().click();
  await page.locator('a[href$="/queries/"]').first().click();
  await expect(page).toHaveURL(/\/queries\/$/);
  await page.locator('a[href$="/playground/"]').first().click();
  await expect(editor).toBeVisible();
  await expect(editor).toHaveCSS("position", "relative");

  await page.goBack();
  await expect(page).toHaveURL(/\/queries\/$/);
  await page.goForward();
  await expect(editor).toBeVisible();
  await expect(editor).toHaveCSS("position", "relative");
});

test("shows page navigation inside the content", async ({ page }) => {
  await page.goto("/queries/");
  const navigation = page.locator("main .pysely-page-nav");
  await expect(navigation.getByRole("link", { name: "← Getting started" })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Schema and typing →" })).toBeVisible();
  await expect(page.locator(".md-footer__link")).toHaveCount(0);
});

test("switches and remembers documentation choices", async ({ page }) => {
  await page.goto("/getting-started/");
  const installTabs = page.locator(".tabbed-set").first();
  await installTabs.getByText("pip", { exact: true }).click();
  await expect(installTabs.locator('input[type="radio"]').nth(1)).toBeChecked();

  await page.goto("/dialects/");
  const dialectTabs = page.locator(".tabbed-set").first();
  const packageTabs = dialectTabs.locator(".tabbed-set").first();
  await expect(packageTabs.locator('input[type="radio"]').nth(1)).toBeChecked();
  await dialectTabs.getByText("MySQL", { exact: true }).click();
  await expect(dialectTabs.locator(':scope > input[type="radio"]').nth(1)).toBeChecked();
  await expect(dialectTabs).toContainText("asyncmy");
});

test("uses readable tab URLs", async ({ page }) => {
  await page.goto("/dialects/");
  const dialectTabs = page.locator(".tabbed-set").first();
  await dialectTabs.getByText("MySQL", { exact: true }).click();
  await expect(page).toHaveURL(/#mysql$/);

  const mysql = dialectTabs.locator(":scope > .tabbed-content > .tabbed-block").nth(1);
  await mysql.getByText("pip", { exact: true }).click();
  await expect(page).toHaveURL(/#mysql-pip$/);

  await page.goto("/dialects/#sqlite");
  await expect(page.locator("#sqlite")).toBeChecked();
  await expect(page.locator('input[id^="__tabbed_"]')).toHaveCount(0);
});

test("regenerates the typed interface from the schema editor", async ({ page }) => {
  await page.goto("/playground/");
  await expect(page.locator("#playground-intelligence-status")).toContainText("suggestions ready");
  await expect(page.locator("#playground-status")).toHaveText("Compiled", { timeout: 40_000 });

  // A column added in the schema editor must become usable in the query editor
  // without a rebuild: the playground runs `pysely codegen` on every run.
  await page.evaluate(() => {
    const monaco = (window as any).monaco;
    const schema = monaco.editor.getModel(monaco.Uri.parse("file:///workspace/schema.py"));
    schema.setValue(schema.getValue().replace("    last_name: str | None\n", "    last_name: str | None\n    nickname: str | None\n"));
  });
  await page.evaluate(code => {
    const monaco = (window as any).monaco;
    monaco.editor.getModel(monaco.Uri.parse("file:///workspace/query.py")).setValue(code);
  }, `from database import DatabaseSchema
from playground import dialect
from pysely import Pysely

db = Pysely.create(schema=DatabaseSchema, dialect=dialect)
compiled = db.select_from("person").select("nickname").compile()
`);

  await expect(page.locator("#playground-sql")).toContainText('select "nickname"', { timeout: 40_000 });
  await expect(page.locator("#playground-status")).toHaveText("Compiled");

  const markers = () => page.evaluate(() => {
    const monaco = (window as any).monaco;
    return monaco.editor.getModelMarkers({}).filter(
      (item: any) => item.resource.path === "/workspace/query.py",
    ).length;
  });
  await expect.poll(markers, { timeout: 40_000 }).toBe(0);
});

test("shows the generated module in an output tab", async ({ page }) => {
  await page.goto("/playground/");
  await expect(page.locator("#playground-status")).toHaveText("Compiled", { timeout: 40_000 });
  await expect(page.locator("#playground-generated")).toBeHidden();
  await page.locator("#playground-tab-generated").click();
  await expect(page.locator("#playground-generated")).toBeVisible();
  await expect(page.locator("#playground-sql")).toBeHidden();
  await expect(page.locator("#playground-generated-code")).toContainText("class DatabaseSchema(GeneratedSchema[DatabaseClient]):");
  // Read-only views are static: only the two editable panes are Monaco editors,
  // but both views are syntax highlighted.
  expect(await page.evaluate(() => (window as any).monaco.editor.getEditors().length)).toBe(2);
  expect(await page.locator("#playground-generated-code [class^=mtk]").count()).toBeGreaterThan(10);
  await page.locator("#playground-tab-sql").click();
  await expect(page.locator("#playground-sql")).toBeVisible();
  expect(await page.locator("#playground-sql [class^=mtk]").count()).toBeGreaterThan(3);
});

test("fits the workbench to the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/playground/");
  await expect(page.locator("#playground-query .monaco-editor")).toBeVisible();
  const bottom = await page.evaluate(() => document.querySelector("#playground-workbench")!.getBoundingClientRect().bottom);
  expect(bottom).toBeLessThanOrEqual(900);
  expect(bottom).toBeGreaterThan(820);
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
  // Standard mode: no "type of X is unknown" cascade across the rest of the chain.
  expect(result.some((item: any) => item.code === "reportUnknownMemberType")).toBe(false);
  expect(result.some((item: any) => item.owner === "pysely")).toBe(false);
  const argument = result.find((item: any) => item.code === "reportArgumentType")!;
  expect(argument.start).toBe(argument.end);
});

test("preserves Pyright diagnostics for an invalid where column", async ({ page }) => {
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
  await expect.poll(markers).toEqual(expect.arrayContaining([
    expect.objectContaining({ code: "reportArgumentType", owner: "pyright" }),
  ]));
  const marker = (await markers()).find((item: any) => item.code === "reportArgumentType")!;
  expect(marker.start).toBe(marker.end);
});
