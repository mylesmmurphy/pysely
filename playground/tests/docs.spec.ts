import { expect, test } from "@playwright/test";

const pages = [
  "/", "/getting-started/", "/queries/", "/typing/", "/typgen/",
  "/dialects/", "/project-status/", "/ROADMAP/", "/playground/",
  "/adr/0001-immutable-ast/", "/adr/0002-binding-profiles/",
  "/adr/0003-portable-typing/", "/adr/0004-diagnostic-recovery/",
  "/adr/0004-pglite-runtime/", "/adr/0005-pool-ownership/",
  "/adr/0006-generated-typed-interfaces/", "/adr/0007-type-only-typgen/",
];

for (const width of [390, 1440]) {
  test(`all documentation pages stay readable at ${width}px`, async ({ page }) => {
    test.setTimeout(90_000);
    await page.setViewportSize({ width, height: 900 });
    for (const route of pages) {
      const response = await page.goto(route);
      expect(response?.status(), route).toBe(200);
      if (route === "/playground/") {
        await expect(page.locator("#playground-workbench")).toBeVisible();
      } else {
        await expect(page.locator("main h1")).toBeVisible();
      }
      const overflow = await page.evaluate(() =>
        document.documentElement.scrollWidth > window.innerWidth + 1,
      );
      expect(overflow, `${route} overflows the viewport`).toBe(false);
      const paragraphs = await page.locator("main .md-typeset p").allTextContents();
      for (const paragraph of paragraphs) {
        expect(
          paragraph.trim().split(/\s+/).length,
          `${route}: paragraph is too dense: ${paragraph}`,
        ).toBeLessThanOrEqual(60);
      }
    }
  });
}
