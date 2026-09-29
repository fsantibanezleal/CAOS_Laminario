// R-1105 and R-1106 on the stage, measured from the viewer. A focal stack: changing plane keeps the view where it was
// (the same viewport bounds), shows the chosen plane's image, and names it by its depth. A polarised pair: the toggle
// shows crossed polars and back on the same field, and the rotation is shown in degrees and applied to the view.
// Needs images the tile server can open.
import { join } from "node:path";
import { chromium } from "playwright";
import { exampleSlides, openPlace, outDir, requireApi, serve } from "./lib/serve.mjs";

await requireApi();
const { stack, pair } = await exampleSlides();
const out = outDir("stage");
const failures = [];
const passed = [];
const stop = await serve();
const browser = await chromium.launch();

async function openStage(record, asset) {
  const { context, page } = await openPlace(browser, `/s/${record.id}/stage/${asset.id}`,
    { width: 1280, room: "lamplit", lang: "en", reducedMotion: "reduce" });
  const ready = await page.waitForFunction(() => {
    const v = document.querySelector("[data-testid=stage-viewer]")?.osd;
    return v && v.world.getItemCount() > 0;
  }, null, { timeout: 30_000 }).catch(() => null);
  return { context, page, ready };
}

const bounds = (page) => page.evaluate(() => {
  const b = document.querySelector("[data-testid=stage-viewer]").osd.viewport.getBounds(true);
  return [b.x, b.y, b.width, b.height];
});

try {
  if (!stack) failures.push("no slide the API serves has a focal stack");
  else {
    const planes = stack.assets.filter((a) => a.role === "z_plane").sort((a, b) => a.plane.index - b.plane.index);
    const { context, page, ready } = await openStage(stack, planes[0]);
    if (!ready) failures.push(`${stack.id}: the stage did not open the stack`);
    else {
      await page.locator("[data-objective]").nth(2).click();
      await page.waitForTimeout(300);
      const before = await bounds(page);
      const target = Math.floor(planes.length / 2);
      await page.locator("[data-testid=plane]").fill(String(target));
      await page.waitForFunction((id) => document.querySelector("[data-testid=stage-viewer]").dataset.asset === String(id),
        planes[target].id, { timeout: 10_000 }).catch(() => null);
      await page.waitForTimeout(1500);
      const after = await bounds(page);
      const moved = Math.max(...before.map((v, i) => Math.abs(v - after[i])));
      if (moved > 1e-9) failures.push(`${stack.id}: changing plane moved the view by ${moved}`);
      const label = await page.locator("label[for=stage-plane]").textContent();
      const depth = planes[target].plane.depth_um;
      if (!label.includes(`${depth} µm`)) failures.push(`${stack.id}: the plane is named "${label}", not by ${depth} µm`);
      const shown = await page.locator("[data-testid=stage-viewer]").getAttribute("data-asset");
      if (shown !== String(planes[target].id)) failures.push(`${stack.id}: plane ${target} is not the image on view`);
      await page.screenshot({ path: join(out, `${stack.id}-plane-${target}.png`) });
      if (!failures.some((f) => f.startsWith(stack.id))) passed.push(`stack ${stack.id}: plane ${target} at ${depth} µm, view kept`);
    }
    await context.close();
  }

  if (!pair) failures.push("no slide the API serves has a polarised pair");
  else {
    const ppl = pair.assets.find((a) => a.role === "polarised" && a.polarisation.state === "ppl");
    const { context, page, ready } = await openStage(pair, ppl);
    if (!ready) failures.push(`${pair.id}: the stage did not open the pair`);
    else {
      const opacity = () => page.evaluate(() => {
        const w = document.querySelector("[data-testid=stage-viewer]").osd.world;
        return [w.getItemAt(0).getOpacity(), w.getItemAt(1).getOpacity()];
      });
      const before = await bounds(page);
      await page.locator("[data-polar=xpl]").click();
      await page.waitForTimeout(400);
      const [, xpl] = await opacity();
      if (xpl !== 1) failures.push(`${pair.id}: crossed polars is at opacity ${xpl}`);
      await page.screenshot({ path: join(out, `${pair.id}-xpl.png`) });
      await page.locator("[data-polar=ppl]").click();
      await page.waitForTimeout(400);
      if ((await opacity())[1] !== 0) failures.push(`${pair.id}: plane-polarised light did not come back`);
      const again = await bounds(page);
      const moved = Math.max(...before.map((v, i) => Math.abs(v - again[i])));
      if (moved > 1e-9) failures.push(`${pair.id}: the toggle moved the view`);
      await page.getByRole("button", { name: "Rotate right" }).click();
      await page.waitForTimeout(400);
      const rotation = await page.evaluate(() => document.querySelector("[data-testid=stage-viewer]").osd.viewport.getRotation());
      const shown = await page.locator("[data-testid=rotation]").textContent();
      if (rotation !== 90 || !shown.includes("90°")) failures.push(`${pair.id}: rotated ${rotation}, shown "${shown}"`);
      await page.screenshot({ path: join(out, `${pair.id}-rotated.png`) });
      if (!failures.some((f) => f.startsWith(pair.id))) passed.push(`pair ${pair.id}: PPL and XPL on one field, rotated 90°`);
    }
    await context.close();
  }
} finally {
  await browser.close();
  await stop();
}
for (const p of passed) console.log(`  ${p}`);
for (const f of failures) console.error(f);
console.log(`stage: ${passed.length} checks passed, ${failures.length} failures; screenshots in ${out}`);
process.exit(failures.length ? 1 : 0);
