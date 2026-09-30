// The glass-slide interface (U17), against the real build and the API over the base collection (or the live site with
// LAMINARIO_GATE_ORIGIN):
//
// R-1701  every set of the collection is drawn as glass slides in a 3D scene, as many as the place holds, each placed on
//         the stage where a pointer reaches it (the landing's collections, a collection's drawers, a drawer's groups
//         and slides, a search, the Identify queue)
// R-1702  no box is left: no element keeps the old boxes' look (a 1 px border round a 6 px radius on an opaque ground),
//         no cabinet or drawer front; the glass plates and panels are there
// R-1704  an arrangement chosen on one set is shown by every set of the page, and kept after a reload
// R-1705  the carousel pattern: a labelled group; Next does not move the focus; the arrow keys move the chosen slide and a
//         ring shows it on the stage; Enter opens it; nothing turns by itself
// R-1706  under reduced motion the scene cuts: a new placement is final at once
// R-1708  drawn flat, the sets are glass slides at one scale, never boxes
//
// Screenshots go to .gates/glass/.
import { join } from "node:path";
import { chromium } from "playwright";
import { glassIds, glassReady, openGlass } from "./lib/glass.mjs";
import { API, ORIGIN, openPlace, outDir, requireApi, serve } from "./lib/serve.mjs";

const api = await requireApi();
const out = outDir("glass");
const stop = await serve();
const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const failures = [];
const passed = [];
const check = (ok, what) => (ok ? passed : failures).push(what);

const tree = await (await fetch(`${API}/api/collections`)).json();
const collectionsOf = (realm) => (tree.realms.find((r) => r.id === realm)?.children ?? []).length;
const plants = tree.realms.flatMap((r) => r.children ?? []).find((c) => c.id === "life.plants");

/** The sets of the page and what each holds, once every scene has placed its slides. */
async function sets(page) {
  const names = await page.$$eval("[data-glass-set]", (all) => all.map((s) => s.getAttribute("data-glass-set")));
  for (const n of names) await glassReady(page, n).catch(() => undefined);
  return page.$$eval("[data-glass-set]", (all) => all.map((s) => ({
    name: s.getAttribute("data-glass-set"), drawn: s.getAttribute("data-drawn"),
    arrangement: s.getAttribute("data-arrangement"), label: s.getAttribute("aria-label"),
    role: s.getAttribute("aria-roledescription"),
    items: s.querySelectorAll("[data-glass-item]").length,
    placed: s.querySelectorAll("[data-glass-item][data-pick-x]").length,
    flat: s.querySelectorAll("[data-glass-flat]").length,
  })));
}

/** Elements that still look like the old boxes: a 1 px solid border round a radius of 6 px or more, on an opaque ground
 * (controls, the map and the stage excepted). */
async function boxes(page) {
  return page.evaluate(() => {
    const skip = (el) => el.closest("input, button, select, textarea, [role=combobox], .maplibregl-map, [data-glass-stage], "
      + "[data-testid=stage-viewer], [data-testid=slide-object]");
    return [...document.querySelectorAll("body *")].filter((el) => {
      if (skip(el)) return false;
      const cs = getComputedStyle(el);
      const r = parseFloat(cs.borderTopLeftRadius);
      const border = parseFloat(cs.borderTopWidth) === 1 && cs.borderTopStyle === "solid"
        && parseFloat(cs.borderLeftWidth) >= 1;
      const ground = cs.backgroundColor;
      const opaque = ground && !ground.startsWith("rgba(0, 0, 0, 0)") && !/, 0\)$/.test(ground) && ground !== "transparent";
      return border && r >= 6 && opaque && el.getBoundingClientRect().width > 40;
    }).map((el) => `${el.tagName.toLowerCase()}.${[...el.classList].join(".")}`).slice(0, 8);
  });
}

async function plates(page) {
  return page.evaluate(() => [...document.querySelectorAll("body *")].filter((el) => {
    const cs = getComputedStyle(el);
    return el.hasAttribute("data-glass-panel") || (parseFloat(cs.borderTopWidth) === 12 && cs.borderImageSource !== "none");
  }).length);
}

try {
  // R-1701 and R-1702 on each place, at a desktop width, in daylight.
  const places = [
    { path: "/", expect: { life: collectionsOf("life"), earth: collectionsOf("earth"), matter: collectionsOf("matter") } },
    { path: "/c/plants", expect: { drawers: (plants?.children ?? []).length } },
    { path: "/c/rocks/igneous", expect: {} },
    { path: "/search", expect: {} },
    { path: "/identify?badge=any", expect: {} },
  ];
  for (const place of places) {
    const { context, page } = await openPlace(browser, place.path, { width: 1280, room: "daylight", lang: "en" });
    const found = await sets(page);
    check(found.length > 0, `R-1701: ${place.path} shows ${found.length} sets of glass slides`);
    for (const s of found) {
      check(s.drawn === "3d" && s.role === "carousel" && Boolean(s.label),
        `R-1701: ${place.path} ${s.name} is a labelled carousel drawn in 3D (${s.drawn}, ${s.role}, "${s.label}")`);
      check(s.items > 0 && s.placed > 0, `R-1701: ${place.path} ${s.name} holds ${s.items} slides, ${s.placed} placed on the stage`);
      const wanted = place.expect[s.name];
      if (wanted !== undefined) check(s.items === wanted, `R-1701: ${place.path} ${s.name} holds ${s.items} of ${wanted}`);
    }
    const left = await boxes(page);
    check(left.length === 0, `R-1702: ${place.path} keeps no box (${left.join(", ") || "none"})`);
    const old = await page.evaluate(() => document.querySelectorAll("[class*='drawerLines'], [class*='cornice'], [class*='_front_']").length);
    check(old === 0, `R-1702: ${place.path} has no cabinet or drawer front (${old})`);
    const glassPlates = await plates(page);
    check(glassPlates > 0, `R-1702: ${place.path} draws its panels as glass (${glassPlates} plates)`);
    await page.screenshot({ path: join(out, `${place.path.replace(/[/?=]/g, "_")}.png`), fullPage: true });
    await context.close();
  }

  // R-1701 by pointer: the landing's Plants slide opened on its stage.
  {
    const { context, page } = await openPlace(browser, "/", { width: 1280, room: "daylight", lang: "en" });
    await openGlass(page, "life", "life.plants");
    check(new URL(page.url()).pathname === "/c/plants", `R-1701: Plants opened by pointer on the stage (${page.url()})`);
    await context.close();
  }

  // R-1704: an arrangement for every set of the page, kept after a reload.
  {
    const { context, page } = await openPlace(browser, "/", { width: 1280, room: "daylight", lang: "en" });
    await sets(page);
    for (const arrangement of ["drawer", "box", "folder", "carousel"]) {
      const names = { drawer: "Cabinet drawer", box: "Slide box", folder: "Folder", carousel: "Carousel" };
      await page.locator("[data-glass-set]").first().getByRole("radio", { name: names[arrangement] }).click();
      await page.waitForTimeout(400);
      const all = await sets(page);
      check(all.every((s) => s.arrangement === arrangement),
        `R-1704: ${arrangement} chosen on one set: ${all.map((s) => s.arrangement).join(", ")}`);
      await page.screenshot({ path: join(out, `arrangement-${arrangement}.png`), fullPage: false });
      if (arrangement === "folder") {
        await page.reload({ waitUntil: "networkidle" });
        const kept = await sets(page);
        check(kept.every((s) => s.arrangement === "folder"), "R-1704: the folder is kept after a reload");
      }
    }
    await context.close();
  }

  // R-1705: the carousel pattern.
  {
    const { context, page } = await openPlace(browser, "/c/plants", { width: 1280, room: "daylight", lang: "en" });
    await glassReady(page, "drawers");
    const set = page.locator('[data-glass-set="drawers"]');
    const ids = await glassIds(page, "drawers");
    const position = () => set.locator("[aria-live=polite]").first().textContent();
    const next = set.getByRole("button", { name: /next/i });
    await next.click();
    check((await position())?.trim().startsWith("2"), `R-1705: Next chose the second slide (${await position()})`);
    check(await page.evaluate(() => document.activeElement?.getAttribute("aria-label")) === "Next slide",
      "R-1705: Next keeps the focus on itself");
    await set.locator(`[data-glass-item="${ids[1]}"]`).focus();
    await page.keyboard.press("ArrowRight");
    await page.waitForTimeout(700);
    check((await position())?.trim().startsWith("3"), `R-1705: the right arrow chose the third slide (${await position()})`);
    const ring = await set.evaluate((s) => {
      const r = [...s.querySelectorAll("span")].find((el) => getComputedStyle(el).borderTopWidth === "3px"
        && getComputedStyle(el).position === "absolute");
      return r ? r.getBoundingClientRect().width : 0;
    });
    check(ring > 20, `R-1705: a ring shows the focused slide on the stage (${Math.round(ring)} px wide)`);
    const before = await position();
    await page.waitForTimeout(3000);
    check(await position() === before, "R-1705: nothing turns by itself");
    await page.keyboard.press("Enter");
    await page.waitForURL((url) => url.pathname === `/c/plants/${ids[2].split(".").slice(2).join("/")}`, { timeout: 10_000 })
      .then(() => check(true, "R-1705: Enter opened the chosen slide"),
        () => check(false, `R-1705: Enter did not open ${ids[2]} (${page.url()})`));
    await context.close();
  }

  // R-1706: under reduced motion the new placement is final at once.
  {
    const { context, page } = await openPlace(browser, "/c/plants", { width: 1280, room: "daylight", lang: "en",
      reducedMotion: "reduce" });
    await glassReady(page, "drawers");
    const set = page.locator('[data-glass-set="drawers"]');
    const ids = await glassIds(page, "drawers");
    await set.getByRole("button", { name: /next/i }).click();
    const pick = () => set.locator(`[data-glass-item="${ids[1]}"]`).evaluate((a) => `${a.dataset.pickX},${a.dataset.pickY}`);
    await page.waitForTimeout(120);
    const soon = await pick();
    await page.waitForTimeout(900);
    check(soon === await pick(), `R-1706: under reduced motion the chosen slide is in place at once (${soon})`);
    await context.close();
  }

  // R-1708: drawn flat, glass slides at one scale, never boxes.
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    await context.addInitScript(() => { localStorage.setItem("laminario.glass", "flat"); localStorage.setItem("laminario.lang", "en"); });
    const page = await context.newPage();
    await page.goto(`${ORIGIN}/c/plants`, { waitUntil: "networkidle" });
    const found = await sets(page);
    check(found.length > 0 && found.every((s) => s.drawn === "flat" && s.flat === s.items),
      `R-1708: flat, every set draws its slides as flat glass (${found.map((s) => `${s.flat}/${s.items}`).join(", ")})`);
    const left = await boxes(page);
    check(left.length === 0, `R-1708: flat, no box (${left.join(", ") || "none"})`);
    await page.screenshot({ path: join(out, "flat-plants.png"), fullPage: true });
    await context.close();
  }
} catch (error) {
  failures.push(`the gate stopped: ${error.message.split("\n")[0]}`);
} finally {
  await browser.close();
  await stop();
}
for (const p of passed) console.log(`ok    ${p}`);
for (const f of failures) console.error(`FAIL  ${f}`);
console.log(`glass: API ${api.version} with ${api.slides} slides; ${passed.length} passed, ${failures.length} failed; screenshots in ${out}`);
process.exit(failures.length ? 1 : 0);
