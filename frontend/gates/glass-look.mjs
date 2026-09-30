// Screenshots of the glass interface for review (U17): the landing place, a collection and a drawer, in every
// arrangement, both rooms, at a desktop and a phone width. It waits for the scene to settle (every slide placed on the
// stage) before each picture. Pictures go to .gates/glass-look/.
import { join } from "node:path";
import { chromium } from "playwright";
import { ORIGIN, outDir, serve } from "./lib/serve.mjs";

const PLACES = (process.env.GLASS_PLACES ?? "/,/c/plants,/c/plants/green-algae").split(",");
const ARRANGEMENTS = (process.env.GLASS_ARRANGEMENTS ?? "carousel,drawer,box,folder").split(",");
const ROOMS = (process.env.GLASS_ROOMS ?? "daylight,lamplit").split(",");
const WIDTHS = (process.env.GLASS_WIDTHS ?? "1280,390").split(",").map(Number);

const stop = await serve();
const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const folder = outDir("glass-look");
const report = [];
try {
  for (const width of WIDTHS) {
    for (const room of ROOMS) {
      for (const arrangement of ARRANGEMENTS) {
        const context = await browser.newContext({ viewport: { width, height: width < 600 ? 844 : 900 } });
        await context.addInitScript(([r, a]) => {
          localStorage.setItem("laminario.theme", r);
          localStorage.setItem("laminario.arrangement", a);
        }, [room, arrangement]);
        const page = await context.newPage();
        const errors = [];
        page.on("pageerror", (e) => errors.push(e.message));
        for (const place of PLACES) {
          await page.goto(`${ORIGIN}${place}`, { waitUntil: "domcontentloaded" });
          await page.waitForSelector("[data-glass-set]", { timeout: 30000 });
          // Settled: every set's first slide has its place on the stage written on its link.
          await page.waitForFunction(() => {
            const sets = [...document.querySelectorAll("[data-glass-set]")];
            return sets.length > 0 && sets.every((s) => s.getAttribute("data-drawn") === "flat"
              || s.querySelector("[data-glass-item][data-pick-x]"));
          }, null, { timeout: 60000 }).catch(() => errors.push("the scene never placed its slides"));
          await page.waitForTimeout(1500);
          const name = `${place.replaceAll("/", "_") || "_"}-${arrangement}-${room}-${width}.png`;
          // The first set's stage in view, with its controls and caption.
          await page.locator("[data-glass-set]").first().scrollIntoViewIfNeeded();
          await page.evaluate(() => {
            const set = document.querySelector("[data-glass-set]");
            if (set) window.scrollBy(0, set.getBoundingClientRect().top - 12);
          });
          await page.waitForTimeout(600);
          await page.screenshot({ path: join(folder, name), fullPage: false });
          const sets = await page.$$eval("[data-glass-set]", (all) => all.map((s) => ({
            name: s.getAttribute("data-glass-set"), drawn: s.getAttribute("data-drawn"),
            items: s.querySelectorAll("[data-glass-item]").length,
            placed: s.querySelectorAll("[data-glass-item][data-pick-x]").length })));
          report.push({ place, arrangement, room, width, sets, errors: [...errors] });
          errors.length = 0;
        }
        await context.close();
      }
    }
  }
} finally {
  await browser.close();
  await stop();
}
for (const r of report) console.log(JSON.stringify(r));
