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
selected = joined.select_as("pet.name", "pet_name")

async def inspect() -> None:
    row = await selected.execute_take_first_or_throw()
    row[""]`);
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("Control+Space");
  await expect(page.locator(".suggest-widget.visible")).toContainText("pet_name");
});

test("keeps real execution available", async ({ page }) => {
  await page.goto("/playground/");
  await expect(page.locator("main h1")).not.toBeVisible();
  const header = await page.locator(".md-header").boundingBox();
  const playground = await page.locator("#playground-workbench").boundingBox();
  expect(playground!.y - (header!.y + header!.height)).toBeLessThan(8);
  await expect(page.locator("#playground-status")).toHaveText("Compiled", { timeout: 40_000 });
  await expect(page.locator("#playground-sql")).toContainText(
    'select "first_name", "pet"."name" as "pet_name"',
  );
});
