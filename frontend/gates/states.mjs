// Screenshots of the interactive states on the specimen place, in both rooms, for review before a unit closes:
// keyboard focus, an open tooltip, an open dialog, a toast, a pressed chip. It also asserts what can be asserted:
// the dialog takes focus and gives it back, Escape closes the tooltip, the toast is announced in a live region.
import { join } from "node:path";
import { chromium } from "playwright";
import { ROOMS, openPlace, outDir, serve } from "./lib/serve.mjs";

const out = outDir("states");
const stop = await serve();
const browser = await chromium.launch();
const failures = [];
try {
  for (const room of ROOMS) {
    const { context, page } = await openPlace(browser, "/design", { width: 1280, room, lang: "en" });
    const shot = (name, clip) => page.screenshot({ path: join(out, `${room}-${name}.png`), clip });

    const save = page.getByRole("button", { name: "Save the slide" }).first();
    await save.focus();
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Tab");
    const box = await save.boundingBox();
    await shot("focus", { x: 0, y: box.y - 40, width: 1280, height: 120 });

    const info = page.getByRole("button", { name: "Crossed polars" });
    await info.hover();
    const tip = page.getByRole("tooltip");
    if (!(await tip.isVisible())) failures.push(`${room}: the tooltip did not open on hover`);
    const tipBox = await info.boundingBox();
    await shot("tooltip", { x: Math.max(0, tipBox.x - 300), y: tipBox.y - 120, width: 600, height: 180 });
    await page.keyboard.press("Escape");
    if (await tip.isVisible()) failures.push(`${room}: Escape did not close the tooltip`);

    const del = page.getByRole("button", { name: "Delete" }).first();
    await del.click();
    const dialog = page.getByRole("dialog");
    if (!(await dialog.isVisible())) failures.push(`${room}: the dialog did not open`);
    const inside = await page.evaluate(() => !!document.activeElement?.closest("dialog"));
    if (!inside) failures.push(`${room}: focus did not move into the dialog`);
    await shot("dialog", { x: 0, y: 0, width: 1280, height: 900 });
    await page.keyboard.press("Escape");
    const back = await page.evaluate(() => document.activeElement?.textContent ?? "");
    if (!back.includes("Delete")) failures.push(`${room}: focus did not return to the button that opened the dialog`);

    await save.click();
    const live = page.locator('[role="status"][aria-live="polite"]');
    if (!(await live.getByText("The slide was saved.").isVisible())) failures.push(`${room}: the toast was not announced`);
    await shot("toast", { x: 560, y: 740, width: 720, height: 160 });
    await context.close();
  }
} finally {
  await browser.close();
  await stop();
}
for (const f of failures) console.error(f);
console.log(`states: ${ROOMS.length} rooms, ${failures.length} failures; screenshots in ${out}`);
process.exit(failures.length ? 1 : 0);
