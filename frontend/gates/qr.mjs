// R-082: the QR on the rendered slide label, screenshotted at its on-screen size, decodes to exactly the slide's
// permalink (its QR payload: the permalink in upper case, which opens the same slide). Both rooms, a desktop and a
// tablet width, a few slides of different collections and formats. The clip is the QR with its quiet zone, as a phone
// camera would frame it; nothing is scaled or cleaned before decoding.
import { join } from "node:path";
import jsQR from "jsqr";
import { PNG } from "pngjs";
import { chromium } from "playwright";
import { ROOMS, exampleSlides, openPlace, outDir, requireApi, serve } from "./lib/serve.mjs";

await requireApi();
const examples = await exampleSlides();
const slides = [...new Map([examples.label, examples.stack, examples.pair, examples.single]
  .filter(Boolean).map((r) => [r.id, r])).values()];
const out = outDir("qr");
const stop = await serve();
const browser = await chromium.launch();
const failures = [];
let decoded = 0;
try {
  for (const record of slides) {
    for (const room of ROOMS) {
      for (const width of [1280, 768]) {
        const { context, page } = await openPlace(browser, `/s/${record.id}`, { width, room, lang: "en" });
        await page.waitForSelector("[data-testid=slide-object] .lam-qr");
        const clip = await page.evaluate(() => {
          const qr = document.querySelector("[data-testid=slide-object] .lam-qr").getBoundingClientRect();
          const pad = (qr.width / 25) * 4; // four modules of a symbol of 25 to 29
          return { x: qr.left - pad, y: qr.top + window.scrollY - pad, width: qr.width + 2 * pad, height: qr.height + 2 * pad };
        });
        const name = `${record.id}-${room}-${width}`;
        const shot = await page.screenshot({ clip, fullPage: true, path: join(out, `${name}.png`) });
        const png = PNG.sync.read(shot);
        const found = jsQR(new Uint8ClampedArray(png.data), png.width, png.height, { inversionAttempts: "dontInvert" });
        if (!found) failures.push(`${name}: no QR decoded from a ${Math.round(clip.width)} px clip`);
        else if (found.data !== record.qr_payload) failures.push(`${name}: decoded ${found.data}, expected ${record.qr_payload}`);
        else if (found.data.toLowerCase() !== record.permalink.toLowerCase()) failures.push(`${name}: payload is not the permalink`);
        else decoded += 1;
        await context.close();
      }
    }
  }
} finally {
  await browser.close();
  await stop();
}
for (const f of failures) console.error(f);
console.log(`qr: ${decoded} labels decoded to their permalink, ${failures.length} failures; screenshots in ${out}`);
process.exit(failures.length ? 1 : 0);
