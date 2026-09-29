// The About place in the browser, against the real build and the API over the base collection (U15).
//
// R-084   the About place is reached from the landing place by pointer, through the footer every place shares
// R-1501  the numbers shown are the API's
// R-1502  every source and every licence the API counts has its card, with words
// R-1503  a slide's page gives its citation and each image's attribution, and Copy copies what is shown
// R-1504  the five figures are drawn in the room's colours and every equation is typeset, in both languages
// R-1506  the map's corner links OpenStreetMap to its copyright page
//
// Screenshots go to .gates/about/.
import { join } from "node:path";
import { chromium } from "playwright";
import { API, LANGS, ORIGIN, ROOMS, openPlace, outDir, requireApi, serve } from "./lib/serve.mjs";

await requireApi();
const out = outDir("about");
const stop = await serve();
const browser = await chromium.launch();
const failures = [];
const passed = [];
const check = (ok, what) => (ok ? passed : failures).push(what);
const digits = (s) => Number(String(s).replace(/[^\d]/g, ""));

try {
  const about = await (await fetch(`${API}/api/about`)).json();

  // R-084: from the landing place to About, by pointer.
  {
    const { context, page } = await openPlace(browser, "/", { width: 1280, room: "daylight", lang: "en" });
    await page.locator("footer").getByRole("link", { name: "About the collection" }).click();
    await page.waitForURL(`${ORIGIN}/about`);
    await page.waitForFunction(() => document.activeElement?.tagName === "H1", null, { timeout: 10_000 })
      .catch(() => undefined);
    check(await page.evaluate(() => document.activeElement?.textContent) === "About the collection",
      "R-084: the footer leads to About, whose heading takes the focus");
    await context.close();
  }

  for (const room of ROOMS) for (const lang of LANGS) {
    const tag = `${room}-${lang}`;
    const { context, page } = await openPlace(browser, "/about", { width: 1280, room, lang });
    await page.locator("[data-live=numbers] dd").first().waitFor();
    // R-1501: the numbers are the API's, in the page's order.
    const n = about.numbers;
    const expected = [n.slides, n.by_origin.base ?? 0, n.by_origin.contribution ?? 0, n.wsi, n.images, n.countries,
      n.contributors, n.identifications];
    const shown = (await page.locator("[data-live=numbers] dd").allTextContents()).map(digits);
    check(JSON.stringify(shown) === JSON.stringify(expected), `R-1501 ${tag}: the numbers are the API's (${shown})`);
    // R-1502: a card per source and per licence, each with words.
    for (const s of about.sources) {
      const card = page.locator(`[data-source="${s.id}"]`);
      const text = (await card.textContent()) ?? "";
      check(await card.count() === 1 && text.includes(String(s.images)) && text.length > 80,
        `R-1502 ${tag}: the ${s.id} card, with its ${s.images} images and its words`);
    }
    check(await page.locator("[data-licence]").count() === about.licences.length,
      `R-1502 ${tag}: a card for each of the ${about.licences.length} licences`);
    // R-1504: the figures drawn, the equations typeset.
    const figures = await page.locator("figure[data-figure] svg").evaluateAll((svgs) => svgs.map((svg) => ({
      w: svg.getBoundingClientRect().width, fill: getComputedStyle(svg.querySelector("rect")).fill })));
    check(figures.length === 5 && figures.every((f) => f.w > 200), `R-1504 ${tag}: five figures drawn`);
    if (lang === "en") {
      const fill = figures[0]?.fill;
      check(Boolean(fill) && fill !== "rgb(0, 0, 0)", `R-1504 ${tag}: the figures take the room's colours (${fill})`);
      if (room === "daylight") globalThis.daylightFill = fill;
      else check(fill !== globalThis.daylightFill, "R-1504: the figures change with the room");
    }
    const maths = await page.evaluate(() => ({ blocks: document.querySelectorAll("[class*=math] .katex-display").length,
      inline: document.querySelectorAll("p .katex").length, errors: document.querySelectorAll(".katex-error").length }));
    check(maths.blocks === 6 && maths.inline > 10 && maths.errors === 0,
      `R-1504 ${tag}: every equation typeset (${maths.blocks} displayed, ${maths.inline} inline, ${maths.errors} errors)`);
    const title = await page.locator("h1").textContent();
    check(title === (lang === "es" ? "Acerca de la colección" : "About the collection"), `${tag}: the page's language`);
    await page.screenshot({ path: join(out, `about-${tag}.png`), fullPage: true });
    await context.close();
  }

  // A section opened from its address is in view once the numbers have arrived.
  {
    const { context, page } = await openPlace(browser, "/about#licences", { width: 1280, room: "daylight", lang: "en" });
    await page.locator("[data-licence]").first().waitFor();
    await page.waitForTimeout(300);
    const top = await page.locator("#licences").evaluate((el) => el.getBoundingClientRect().top);
    check(top >= -2 && top < 200, `/about#licences opens at the licences (top ${Math.round(top)} px)`);
    await context.close();
  }

  // R-1506: the map credits OpenStreetMap with a link to its copyright page.
  {
    const { context, page } = await openPlace(browser, "/map", { width: 1280, room: "daylight", lang: "en" });
    const credit = page.locator("a[data-osm-credit]");
    const ok = await credit.first().waitFor({ timeout: 20_000 }).then(() => true, () => false);
    check(ok && await credit.getAttribute("href") === "https://www.openstreetmap.org/copyright",
      "R-1506: the map links OpenStreetMap to its copyright page");
    await context.close();
  }

  // R-1503: a slide's citation and its images' attributions, copied as shown.
  {
    const first = (await (await fetch(`${API}/api/slides?node=life.insects&limit=1`)).json()).items[0];
    const record = await (await fetch(`${API}/api/slides/${first.id}`)).json();
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 },
      permissions: ["clipboard-read", "clipboard-write"] });
    await context.addInitScript(() => {
      try { localStorage.setItem("laminario.lang", "en"); } catch { /* */ }
    });
    const page = await context.newPage();
    await page.goto(`${ORIGIN}/s/${record.id}`, { waitUntil: "networkidle" });
    const lines = page.locator("[data-cite]");
    await lines.first().waitFor();
    check(await lines.count() === 1 + record.assets.length,
      `R-1503: the citation and one attribution per image (${await lines.count()} for ${record.assets.length} images)`);
    const citation = (await lines.first().locator("p").textContent()) ?? "";
    check(citation.startsWith("Laminario (") && citation.includes(record.permalink),
      "R-1503: the slide's citation names Laminario and the permalink");
    const image = (await lines.nth(1).locator("p").textContent()) ?? "";
    const asset = record.assets[0];
    check(image.includes(asset.licence.short_name) && image.includes(asset.licence.uri) && /adapted/.test(image),
      "R-1503: an image's attribution names its licence with the link and says it is adapted");
    await lines.first().getByRole("button").click();
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    check(copied === citation, "R-1503: Copy copies the citation as shown");
    await page.locator("#cite").scrollIntoViewIfNeeded();
    await page.screenshot({ path: join(out, "cite.png"), fullPage: false });
    await context.close();
  }
} catch (error) {
  failures.push(`the gate stopped: ${error instanceof Error ? error.message : String(error)}`);
} finally {
  await browser.close();
  await stop();
}

for (const p of passed) console.log(`ok    ${p}`);
for (const f of failures) console.error(`FAIL  ${f}`);
console.log(`about: ${passed.length} passed, ${failures.length} failed; screenshots in ${out}`);
process.exit(failures.length ? 1 : 0);
