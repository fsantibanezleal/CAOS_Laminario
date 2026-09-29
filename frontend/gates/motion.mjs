// R-085: with reduced motion set, no transition or animation lasts longer than 0 ms, except opacity fades (which may
// last up to 150 ms). Measures the computed styles of every element (and its ::before and ::after) of every place,
// in both rooms, after pressing the controls that start movement (the slide's move, the switches).
import { chromium } from "playwright";
import { PLACES, ROOMS, openPlace, requireApi, serve, exampleSlides } from "./lib/serve.mjs";

await requireApi();
// The slide and stage places of a slide the API serves (their ids belong to its collection).
const { label } = await exampleSlides();
const stageAsset = label.assets.find((a) => a.family === "micro" && a.status === "ready");
PLACES.push(`/s/${label.id}`, ...(stageAsset ? [`/s/${label.id}/stage/${stageAsset.id}`] : []));

const stop = await serve();
const browser = await chromium.launch();
const failures = [];
let measured = 0;
try {
  for (const path of PLACES) {
    for (const room of ROOMS) {
      const { context, page } = await openPlace(browser, path, { width: 1280, room, lang: "en", reducedMotion: "reduce" });
      const move = page.getByRole("button", { name: "Move the slide" });
      if (await move.count()) await move.click();
      const found = await page.evaluate(() => {
        const ms = (v) => Math.max(...v.split(",").map((x) => (x.trim().endsWith("ms") ? parseFloat(x)
          : parseFloat(x) * 1000)));
        const bad = [];
        let count = 0;
        for (const el of document.querySelectorAll("*")) {
          for (const pseudo of [null, "::before", "::after"]) {
            const s = getComputedStyle(el, pseudo);
            count += 1;
            const transition = ms(s.transitionDuration);
            const animation = s.animationName !== "none" ? ms(s.animationDuration) : 0;
            const onlyOpacity = s.transitionProperty.split(",").every((p) => p.trim() === "opacity");
            if (animation > 0 || (transition > 0 && !(onlyOpacity && transition <= 150))) {
              bad.push(`${el.tagName.toLowerCase()}${pseudo ?? ""}.${String(el.className).split(" ")[0]}: ` +
                `transition ${s.transitionDuration} (${s.transitionProperty}), animation ${s.animationName} ${s.animationDuration}`);
            }
          }
        }
        return { bad: bad.slice(0, 20), count };
      });
      measured += found.count;
      for (const b of found.bad) failures.push(`${path} ${room}: ${b}`);
      await context.close();
    }
  }
} finally {
  await browser.close();
  await stop();
}
for (const f of failures) console.error(f);
console.log(`motion: ${measured} computed styles measured with reduced motion, ${failures.length} moving`);
process.exit(failures.length ? 1 : 0);
