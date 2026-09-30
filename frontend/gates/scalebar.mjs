// R-086: on the stage, at every objective of the turret (optical and digital), the scale bar's length matches the
// physical distance within 1 percent. The distance is measured from the viewer itself (the image pixels a screen
// pixel covers, from OpenSeadragon's own zoom) and the pixel size the API gives, not from the stage's arithmetic;
// the bar's drawn width is read from the page. Needs images the tile server can open.
import { join } from "node:path";
import { chromium } from "playwright";
import { exampleSlides, openPlace, outDir, requireApi, serve } from "./lib/serve.mjs";

await requireApi();
const { all } = await exampleSlides();
const scaled = all.flatMap((r) => r.assets.filter((a) => a.family === "micro" && a.status === "ready" && a.pixel_size_um
  && (a.media.iiif_info_url || a.media.image_url)).slice(0, 1).map((a) => ({ record: r, asset: a }))).slice(0, 3);
const out = outDir("scalebar");
const failures = [];
let measured = 0;
if (!scaled.length) failures.push("no slide the API serves has a micro image with a pixel size");
const stop = await serve();
const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
try {
  for (const { record, asset } of scaled) {
    const { context, page } = await openPlace(browser, `/s/${record.id}/stage/${asset.id}`,
      { width: 1280, room: "lamplit", lang: "en", reducedMotion: "reduce" });
    const opened = await page.waitForFunction(() => {
      const v = document.querySelector("[data-testid=stage-viewer]")?.osd;
      return v && v.world.getItemCount() > 0 && v.world.getItemAt(0).getFullyLoaded?.() !== undefined;
    }, null, { timeout: 30_000 }).catch(() => null);
    if (!opened) {
      failures.push(`${record.id}/${asset.id}: the stage did not open its image`);
      await context.close();
      continue;
    }
    const objectives = await page.locator("[data-objective]").evaluateAll((els) => els.map((e) => e.dataset.objective));
    if (!objectives.length) failures.push(`${record.id}/${asset.id}: no objectives for an image with a pixel size`);
    for (const objective of objectives) {
      await page.locator(`[data-objective="${objective}"]`).click();
      await page.waitForTimeout(400);
      const m = await page.evaluate((pixelUm) => {
        const host = document.querySelector("[data-testid=stage-viewer]");
        const viewer = host.osd;
        const zoom = viewer.world.getItemAt(0).viewportToImageZoom(viewer.viewport.getZoom(true));
        const bar = document.querySelector("[data-testid=scale-bar]");
        const drawn = bar?.querySelector("span")?.getBoundingClientRect().width ?? null;
        return { umPerPx: pixelUm / zoom, um: Number(bar?.dataset.um), drawn, text: bar?.textContent ?? "" };
      }, asset.pixel_size_um);
      const physical = m.drawn * m.umPerPx;
      const error = Math.abs(physical - m.um) / m.um;
      if (!(m.drawn > 0) || !(error <= 0.01)) {
        failures.push(`${record.id}/${asset.id} at ${objective}x: the bar says ${m.text.trim()} and spans ${physical.toFixed(3)} um`);
      } else measured += 1;
      await page.screenshot({ path: join(out, `${record.id}-${asset.id}-${objective}x.png`) });
    }
    await context.close();
  }
} finally {
  await browser.close();
  await stop();
}
for (const f of failures) console.error(f);
console.log(`scalebar: ${measured} objective steps within 1 percent, ${failures.length} failures; screenshots in ${out}`);
process.exit(failures.length ? 1 : 0);
