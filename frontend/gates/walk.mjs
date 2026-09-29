// The pointer walk through the places built so far, against the real build and the API over the base collection.
//
// R-084   from the landing place, every place is reached by clicking (no keyboard, no typed address): the realms,
//         a cabinet, a drawer, a slide, its stage, search, the map, the Identify place, and the way to contribute
//         (sign in, where a visitor who opens /contribute is also sent), and About from the footer
// R-1107  the slide shows every image's source, record, author or rights holder, licence and, for a base slide, SHA-256
// R-1006  after every navigation the new place's heading has the focus; a place reopened from its address (filters
//         included) shows the same results as when it was reached by clicking
// R-1007  every slide in a drawer is drawn at its format's proportion within 1 percent, at one scale for the whole tray,
//         label end first
// R-1008  without its basemap the map still draws, and says so
//
// Screenshots of each step go to .gates/walk/.
import { join } from "node:path";
import { chromium } from "playwright";
import { API, ORIGIN, openPlace, outDir, requireApi, serve } from "./lib/serve.mjs";

const api = await requireApi();
const out = outDir("walk");
const stop = await serve();
const browser = await chromium.launch();
const failures = [];
const steps = [];
const check = (ok, message) => { if (!ok) failures.push(message); };

async function arrived(page, pattern, name) {
  await page.waitForURL(pattern, { timeout: 15_000 });
  // After a navigation inside the page, networkidle is already reached (the document loaded long ago), so the wait
  // returns at once: a place loaded as its own chunk (Identify, Contribute) has not mounted yet. Wait for the place's
  // heading to take the focus, then judge it.
  await page.waitForFunction(() => document.activeElement?.tagName === "H1", null, { timeout: 10_000 })
    .catch(() => undefined);
  await page.waitForLoadState("networkidle");
  const focus = await page.evaluate(() => ({ tag: document.activeElement?.tagName, text: document.activeElement?.textContent }));
  check(focus.tag === "H1", `${name}: the focus is on ${focus.tag} after the navigation, not the place's heading`);
  await page.screenshot({ path: join(out, `${String(steps.length).padStart(2, "0")}-${name}.png`), fullPage: true });
  steps.push(`${name}: ${new URL(page.url()).pathname}${new URL(page.url()).search}`);
}

/** The slides a place shows, and its announced count. */
async function shown(page) {
  await page.waitForFunction(() => !document.querySelector("[aria-busy='true']"));
  return page.evaluate(() => ({
    ids: [...document.querySelectorAll("[data-slide]")].map((a) => a.dataset.slide),
    count: document.querySelector("[role='status']")?.textContent ?? "",
  }));
}

/** R-1007: proportion, one scale, label end first, for every slide of the tray. */
async function measureTray(page, name) {
  const slides = await page.evaluate(() => [...document.querySelectorAll("[data-slide]")].map((a) => {
    const [long, short] = a.dataset.format.split("x").map(Number);
    const glass = a.firstElementChild.getBoundingClientRect();
    const label = a.firstElementChild.firstElementChild.getBoundingClientRect();
    return { id: a.dataset.slide, long, short, w: glass.width, h: glass.height, labelLeft: label.left, glassLeft: glass.left };
  }));
  check(slides.length > 0, `${name}: the tray holds no slide`);
  const scales = slides.map((s) => s.w / s.long);
  for (const s of slides) {
    const error = Math.abs((s.w / s.h) / (s.long / s.short) - 1);
    check(error <= 0.01, `${name}: ${s.id} is drawn at ${(s.w / s.h).toFixed(3)}, its format is ${(s.long / s.short).toFixed(3)}`);
    check(Math.abs(s.labelLeft - s.glassLeft) < 1, `${name}: ${s.id} does not start with its label end`);
  }
  const spread = Math.max(...scales) / Math.min(...scales) - 1;
  check(spread <= 0.005, `${name}: the tray's slides are drawn at different scales (spread ${(spread * 100).toFixed(2)} %)`);
  return slides.length;
}

try {
  const { context, page } = await openPlace(browser, "/", { width: 1280, room: "daylight", lang: "en" });
  await page.screenshot({ path: join(out, "00-landing.png"), fullPage: true });
  steps.push("landing: /");

  // Landing > the Rocks cabinet > the igneous drawer.
  await page.locator('a[href="/c/rocks"]').first().click();
  await arrived(page, "**/c/rocks", "cabinet");
  await page.locator('a[href="/c/rocks/igneous"]').first().click();
  await arrived(page, "**/c/rocks/igneous", "drawer");
  const drawer = await shown(page);
  check(drawer.ids.length > 0, "drawer: no slides in the igneous drawer");
  const measured = await measureTray(page, "drawer");

  // Every slide opens its own place (the slide place arrives with U11).
  const hrefs = await page.evaluate(() => [...document.querySelectorAll("[data-slide]")].map((a) => a.getAttribute("href")));
  check(hrefs.every((h) => /^\/s\/[0-9A-HJKMNP-TV-Z]{8}$/.test(h)), `drawer: a slide links elsewhere: ${hrefs.find((h) => !/^\/s\//.test(h))}`);

  // A facet by pointer narrows the drawer; the address carries it and reopens to the same slides.
  const chip = page.locator("aside [data-value^='modality:']:not([disabled])").last();
  const value = await chip.getAttribute("data-value");
  await chip.click();
  const [facet, id] = value.split(":");
  await page.waitForURL((url) => url.searchParams.getAll(facet).includes(id));
  const filtered = await shown(page);
  check(filtered.ids.length > 0 && filtered.ids.length < drawer.ids.length,
    `drawer: the ${value} filter gave ${filtered.ids.length} of ${drawer.ids.length} slides`);
  const address = page.url();
  steps.push(`facet ${value}: ${filtered.ids.length} slides`);
  // Reopened in the same visitor's browser (its room and language), as a shared link would be.
  const reopened = await context.newPage();
  await reopened.goto(address, { waitUntil: "networkidle" });
  const again = await shown(reopened);
  check(JSON.stringify(again.ids) === JSON.stringify(filtered.ids) && again.count === filtered.count,
    `drawer: reopened from its address it shows ${again.ids.length} slides ("${again.count}"), clicked ${filtered.ids.length} ("${filtered.count}")`);
  await reopened.close();

  // A slide from the tray, then its stage, by pointer (R-084); every image's provenance on the slide (R-1107).
  const picked = filtered.ids[0];
  await page.locator(`[data-slide="${picked}"]`).first().click();
  await arrived(page, `**/s/${picked}`, "slide");
  const record = await (await fetch(`${API}/api/slides/${picked}`)).json();
  await page.waitForSelector("[data-testid=slide-object] svg");
  const rows = await page.evaluate(() => [...document.querySelectorAll("[data-testid=provenance] tbody tr")].map((tr) => ({
    asset: Number(tr.dataset.asset), cells: [...tr.children].map((c) => c.textContent.trim()),
    licence: tr.querySelector("a[href*='creativecommons'], a[href*='publicdomain']")?.getAttribute("href") ?? null,
  })));
  check(rows.length === record.assets.length, `slide: ${rows.length} provenance rows for ${record.assets.length} images`);
  for (const asset of record.assets) {
    const row = rows.find((r) => r.asset === asset.id);
    check(row && row.licence === asset.licence.uri, `slide: image ${asset.id} shows no licence ${asset.licence.uri}`);
    check(row && (asset.creator ?? asset.rights_holder ?? "") !== "" && row.cells.includes(asset.creator ?? asset.rights_holder),
      `slide: image ${asset.id} does not name its author or rights holder`);
    if (asset.source) {
      check(row && row.cells.some((c) => c.includes(asset.source.record_id)), `slide: image ${asset.id} shows no record`);
      if (record.origin === "base") {
        check(row && row.cells.some((c) => asset.source.sha256.startsWith(c) && c.length >= 12),
          `slide: image ${asset.id} shows no SHA-256`);
      }
    }
  }
  const card = page.locator("[data-stage-item]").first();
  const itemHref = await card.getAttribute("href");
  await card.click();
  await arrived(page, `**${itemHref}`, "stage");
  // The viewer is a separate chunk (OpenSeadragon and Annotorious), loaded when the stage opens.
  const viewer = await page.waitForSelector("[data-testid=stage-viewer]", { timeout: 20_000 }).catch(() => null);
  check(viewer !== null, "stage: no viewer");
  await page.locator(`main a[href="/s/${picked}"]`).first().click();
  await arrived(page, `**/s/${picked}`, "slide-again");

  // The trail back to the cabinet, then the masthead to search.
  await page.locator("nav[aria-label] a[href='/c/rocks']").first().click();
  await arrived(page, "**/c/rocks", "cabinet-again");
  await page.locator("header nav a[href='/search']").click();
  await arrived(page, "**/search", "search");
  const everything = await shown(page);
  check(everything.ids.length > 0, "search: with no words it lists no slide");
  // A collection facet by pointer scopes the search to a cabinet.
  await page.locator("aside button[aria-pressed]").filter({ hasText: /Rocks/ }).first().click();
  await page.waitForURL((url) => url.searchParams.get("node") === "earth.rocks");
  const rocks = await shown(page);
  check(rocks.ids.length > 0 && rocks.ids.length <= everything.ids.length, "search: the Rocks cabinet gave no slide");
  steps.push(`search in rocks: ${rocks.count}`);

  // The map, with its basemap.
  await page.locator("header nav a[href='/map']").click();
  await arrived(page, "**/map", "map");
  await page.waitForSelector(".maplibregl-canvas", { timeout: 20_000 });
  const countries = page.locator("section button[aria-pressed]");
  const listed = await countries.count();
  check(listed > 0, "map: no country is listed (the base collection's countries are missing)");
  if (listed > 0) {
    await countries.first().click();
    await page.waitForURL((url) => url.searchParams.has("at"));
    await page.waitForSelector("#map-selected");
    await page.screenshot({ path: join(out, `${String(steps.length).padStart(2, "0")}-map-country.png`), fullPage: true });
    steps.push(`map country: ${new URL(page.url()).searchParams.get("at")}`);
  }

  // Back to the collections from the masthead's wordmark.
  await page.locator("header a[href='/']").first().click();
  await arrived(page, (url) => url.pathname === "/", "landing-again");

  // The Identify place from the masthead (U13).
  await page.locator("header").getByRole("link", { name: "Identify" }).click();
  await arrived(page, (url) => url.pathname === "/identify", "identify");
  steps.push("the Identify place from the masthead");
  await page.locator("header a[href='/']").first().click();
  await arrived(page, (url) => url.pathname === "/", "landing-after-identify");

  // About the collection, from the footer every place shares (U15), and back home by the wordmark.
  await page.locator("footer").getByRole("link", { name: "About the collection" }).click();
  await arrived(page, (url) => url.pathname === "/about", "about");
  check(await page.locator("[data-live=numbers] dd").count() === 8, "about: the collection's numbers are not shown");
  await page.locator("header a[href='/']").first().click();
  await arrived(page, (url) => url.pathname === "/", "landing-after-about");

  // The way to contribute: the masthead's sign-in, whose form leads to the account's places (U12).
  await page.locator("header").getByRole("link", { name: "Sign in" }).click();
  await arrived(page, (url) => url.pathname === "/signin", "signin");
  check(await page.locator("main form input[type=password]").count() === 1, "sign in: no password field");
  check(await page.locator("main a[href='/forgot-password']").count() === 1, "sign in: no way to reset a password");
  await page.locator("main a[href='/forgot-password']").click();
  await arrived(page, (url) => url.pathname === "/forgot-password", "forgot-password");
  await page.goto(`${ORIGIN}/contribute`, { waitUntil: "networkidle" });
  await page.waitForURL((url) => url.pathname === "/signin" && url.searchParams.get("next") === "/contribute");
  steps.push("a visitor opening /contribute is sent to sign in, and returns there after");

  // A place that does not exist says so and leads back.
  await page.goto(`${ORIGIN}/nowhere`, { waitUntil: "networkidle" });
  check(await page.locator("main a[href='/']").count() === 1, "not found: no way back to the collections");
  await context.close();

  // R-1008: the map without its basemap.
  const bare = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await bare.addInitScript(() => { localStorage.setItem("laminario.lang", "en"); });
  await bare.route("**/api/explore/basemap.pmtiles", (route) => route.fulfill({ status: 404, body: "" }));
  const barePage = await bare.newPage();
  const errors = [];
  barePage.on("pageerror", (e) => errors.push(String(e)));
  await barePage.goto(`${ORIGIN}/map`, { waitUntil: "networkidle" });
  await barePage.waitForSelector(".maplibregl-canvas", { timeout: 20_000 });
  await barePage.waitForTimeout(1500);
  const notice = await barePage.getByText("The basemap is not installed").count();
  check(notice === 1, "map without basemap: the page does not say the basemap is missing");
  check(errors.length === 0, `map without basemap: ${errors.join(" | ")}`);
  await barePage.screenshot({ path: join(out, "zz-map-without-basemap.png") });
  await bare.close();
  steps.push(`tray measured: ${measured} slides`);
} catch (error) {
  failures.push(`the walk stopped: ${error.message.split("\n")[0]}`);
} finally {
  await browser.close();
  await stop();
}
for (const s of steps) console.log(`  ${s}`);
for (const f of failures) console.error(f);
console.log(`walk: API ${api.version} with ${api.slides} slides; ${steps.length} steps, ${failures.length} failures; screenshots in ${out}`);
process.exit(failures.length ? 1 : 0);
