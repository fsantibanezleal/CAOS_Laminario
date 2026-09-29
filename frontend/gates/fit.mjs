// R-080: no horizontal page scroll at 360, 768, 1280 and 1920 px, in both rooms and both languages, on every place
// built so far (lib/serve.mjs lists them). Also checks that the page painted in the room and language asked for, and
// saves a full-page screenshot of each case in .gates/fit/ to be read before a unit closes.
import { join } from "node:path";
import { chromium } from "playwright";
import { LANGS, PLACES, ROOMS, WIDTHS, openPlace, outDir, requireApi, serve, exampleSlides } from "./lib/serve.mjs";

await requireApi();
// The slide and stage places of a slide the API serves (their ids belong to its collection).
const { label } = await exampleSlides();
const stageAsset = label.assets.find((a) => a.family === "micro" && a.status === "ready");
PLACES.push(`/s/${label.id}`, ...(stageAsset ? [`/s/${label.id}/stage/${stageAsset.id}`] : []));

const out = outDir("fit");
const stop = await serve();
const browser = await chromium.launch();
const failures = [];
let cases = 0;
try {
  for (const path of PLACES) {
    for (const room of ROOMS) {
      for (const lang of LANGS) {
        for (const width of WIDTHS) {
          const { context, page } = await openPlace(browser, path, { width, room, lang });
          const found = await page.evaluate(() => {
            const root = document.documentElement;
            const wide = [...document.querySelectorAll("body *")].filter((el) => {
              const r = el.getBoundingClientRect();
              return r.width > 0 && r.right > root.clientWidth + 1;
            }).slice(0, 5).map((el) => `${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0]}`);
            return { scroll: root.scrollWidth, client: root.clientWidth, theme: root.dataset.theme, lang: root.lang,
              wide };
          });
          cases += 1;
          const name = `${path.replace(/\W+/g, "") || "home"}-${room}-${lang}-${width}`;
          await page.screenshot({ path: join(out, `${name}.png`), fullPage: true });
          if (found.scroll > found.client) {
            failures.push(`${name}: scrolls sideways (${found.scroll} > ${found.client}); widest: ${found.wide.join(", ")}`);
          }
          if (found.theme !== room || found.lang !== lang) {
            failures.push(`${name}: painted ${found.theme}/${found.lang}, asked ${room}/${lang}`);
          }
          await context.close();
        }
      }
    }
  }
} finally {
  await browser.close();
  await stop();
}
for (const f of failures) console.error(f);
console.log(`fit: ${cases} cases, ${failures.length} failures; screenshots in ${out}`);
process.exit(failures.length ? 1 : 0);
