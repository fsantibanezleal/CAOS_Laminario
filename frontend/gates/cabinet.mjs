// R-1408 end to end in the browser, in its own sandbox (gates/lib/sandbox.mjs): a contributor publishes two slides in
// two collections (through the API and tusd; the contribute gate walks that part in the browser) and an identifier
// agrees with one. A visitor opens a slide, follows its contributor to their cabinet, finds a drawer per collection,
// selects both slides and prints their labels on a stock from a chosen position with a printer offset, and prints the
// stock's test page; the offset stays on the device for that stock. The identifier's cabinet lists the identification
// and says the community agrees. Signed in, the contributor reaches their cabinet from the account menu and exports
// their slides with the exact place of an obscured one (R-1407), which no public answer shows. Then the cabinet, its
// identifications and the print dialog fit at every width, room and language (R-080), and nothing moves with reduced
// motion (R-085).
//
// The case pairs two real files, as the identify gate does: a scan of a thin section of the Siilinjarvi apatite ore
// (Wikimedia Commons, "Thin section scan crossed polarizers Siilinjärvi R636-116.75.jpg", by kallerna, CC BY-SA 4.0;
// 3.97 um per pixel) and a photograph of a place. The apatite slide reuses the scan: the ore is apatite-bearing.
//
//   LAMINARIO_FIXTURES   the data vault (samples/commons_thin_xpl.jpg, samples/commons_san_cristobal_gps.jpg)
//
// and the sandbox's own variables and ports.
import { existsSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";
import { API, PASSWORD, member, need, startSandbox, tusUpload, until } from "./lib/sandbox.mjs";
import { LANGS, ORIGIN, ROOMS, WIDTHS, outDir } from "./lib/serve.mjs";

const failures = [];
const passed = [];
const check = (ok, what) => (ok ? passed : failures).push(what);
const shows = (locator, timeout = 15_000) => locator.first().waitFor({ state: "visible", timeout }).then(() => true,
  () => false);

const fixtures = need("LAMINARIO_FIXTURES");
const SCAN = join(fixtures, "samples", "commons_thin_xpl.jpg");
const PHOTO = join(fixtures, "samples", "commons_san_cristobal_gps.jpg");
for (const file of [SCAN, PHOTO]) if (!existsSync(file)) throw new Error(`missing fixture ${file}`);

const out = outDir("cabinet");
const sb = await startSandbox("cabinet");
let browser = null;

const PEOPLE = {
  maker: { role: "contributor", email: "gate.maker@example.org", name: "Gate Contributor" },
  one: { role: "identifier", email: "gate.one@example.org", name: "Gate Identifier" },
};
const EXACT = { lat: 63.1553, lon: 27.7275 };

async function api(cookie, method, path, body) {
  const r = await fetch(`${API}${path}`, { method, headers: { Cookie: cookie,
    ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
  const text = await r.text();
  let json = null;
  try { json = text ? JSON.parse(text) : null; } catch { json = text; }
  return { status: r.status, json, text };
}

/** Requests sent and not yet answered, so a wait that times out can say what it was waiting behind. */
const pending = new Map();

async function newContext(width = 1280, room = "daylight", lang = "en", storageState = undefined) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: "reduce",
    colorScheme: room === "lamplit" ? "dark" : "light", storageState });
  context.on("request", (r) => pending.set(r, Date.now()));
  context.on("requestfinished", (r) => pending.delete(r));
  context.on("requestfailed", (r) => pending.delete(r));
  context.on("close", () => pending.clear());
  await context.addInitScript(([r, l]) => {
    try { localStorage.setItem("laminario.theme", r); localStorage.setItem("laminario.lang", l); } catch { /* */ }
  }, [room, lang]);
  return context;
}

/** A contribution taken through tusd and the worker to publication; returns its short id. */
async function publish(cookie, anchor, catalogue, place) {
  const placed = await api(cookie, "POST", "/api/placement", { anchor });
  if (!placed.json?.suggestion) throw new Error(`no placement for ${anchor.name}: ${placed.text}`);
  const created = await api(cookie, "POST", "/api/slide-cases", {
    slide: { format: "petro_27x46", coverslip: "none", preparation: "thin_section", catalogue_number: catalogue },
    specimen: { anchor, locality_text: "Siilinjärvi apatite mine, Finland", country: "FI", ...place },
    placement: { node: placed.json.suggestion },
    assets: [
      { family: "macro", role: "place", upload_id: `gate-photo-${catalogue.replace(/[^A-Za-z0-9_+-]/g, "-")}`, creator: "Mulatoenchile (Wikimedia Commons)",
        licence: "https://creativecommons.org/licenses/by-sa/3.0/" },
      { family: "micro", role: "single", upload_id: `gate-scan-${catalogue.replace(/[^A-Za-z0-9_+-]/g, "-")}`, creator: "kallerna (Wikimedia Commons)",
        licence: "https://creativecommons.org/licenses/by-sa/4.0/", pixel_size_um: 3.97, modality: "polarised_xpl" },
    ],
  });
  if (created.status !== 201) throw new Error(`the case ${catalogue}: ${created.status} ${created.text}`);
  const id = created.json.id;
  const draft = await api(cookie, "GET", `/api/slide-cases/${id}`);
  for (const image of draft.json.images) {
    await tusUpload(cookie, id, image.asset_id, image.family === "macro" ? PHOTO : SCAN, "image/jpeg");
  }
  await until(async () => (await api(cookie, "GET", `/api/slide-cases/${id}`)).json.images.every((i) => i.has_file),
    240_000, `${catalogue}: both files accepted`);
  const submitted = await api(cookie, "POST", `/api/slide-cases/${id}/submit`);
  if (submitted.status !== 200) throw new Error(`submit ${catalogue}: ${submitted.status} ${submitted.text}`);
  await until(async () => (await api(cookie, "GET", `/api/slide-cases/${id}`)).json.status === "published",
    300_000, `${catalogue} published`);
  return { id, node: placed.json.suggestion };
}

/** The PDF behind a link: its status, type and page count. */
async function pdfAt(page, href) {
  const r = await page.request.get(new URL(href, ORIGIN).toString());
  const body = await r.body();
  const pages = (body.toString("latin1").match(/\/Type\s*\/Page(?![s\w])/g) ?? []).length;
  return { status: r.status(), type: r.headers()["content-type"], pdf: body.subarray(0, 5).toString() === "%PDF-",
    pages, disposition: r.headers()["content-disposition"] ?? "" };
}

/** RFC 4180 rows: quoted fields may hold commas, quotes (doubled) and line breaks. */
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i += 1; } else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (ch !== "\r") field += ch;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
}

const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

try {
  const cookies = {};
  for (const [key, who] of Object.entries(PEOPLE)) {
    cookies[key] = await member(sb.invite(who.role, who.email), who.email, who.name);
  }
  const maker = (await api(cookies.maker, "GET", "/api/session")).json.handle;
  const one = (await api(cookies.one, "GET", "/api/session")).json.handle;
  check(maker === "gate-contributor" && one === "gate-identifier",
    `R-1401: each account's handle is made from its display name (${maker}, ${one})`);

  // Two slides in two collections: a carbonatite (rocks), obscured, and apatite (minerals).
  const carbonatite = { kind: "rock", ref: "carbonatite", name: "Carbonatite" };
  const found = await api("", "GET", "/api/anchors/search?kind=mineral&q=apatite&limit=5");
  const apatiteRef = found.json.find((s) => /^apatite/i.test(s.name)) ?? found.json[0];
  const apatite = { kind: "mineral", ref: apatiteRef.ref, name: apatiteRef.name,
    ...(apatiteRef.classification ? { classification: apatiteRef.classification } : {}) };
  const rock = await publish(cookies.maker, carbonatite, "R636-116.75",
    { geoprivacy: "obscured", coordinates: { ...EXACT, uncertainty_m: 50 } });
  const mineral = await publish(cookies.maker, apatite, "R636-116.76", { geoprivacy: "open" });
  check(rock.node.split(".").slice(0, 2).join(".") !== mineral.node.split(".").slice(0, 2).join("."),
    `the two slides lie in two collections (${rock.node}, ${mineral.node})`);
  const agreed = await api(cookies.one, "POST", `/api/slides/${rock.id}/identifications`,
    { anchor: carbonatite, body: "Calcite with apatite and phlogopite." });
  check(agreed.status === 201, "the identifier agrees with the carbonatite");

  browser = await chromium.launch();

  // A visitor: from the slide to its contributor's cabinet (R-1408).
  const visitor = await newContext();
  const page = await visitor.newPage();
  await page.goto(`${ORIGIN}/s/${rock.id}`, { waitUntil: "networkidle" });
  const contributor = page.locator(`a[data-contributor="${maker}"]`);
  check(await shows(contributor), "the slide names its contributor, linked to their cabinet");
  await contributor.click();
  await page.waitForURL(`${ORIGIN}/people/${maker}`);
  await page.waitForFunction(() => document.activeElement?.tagName === "H1", null, { timeout: 10_000 })
    .catch(() => undefined);
  check(await shows(page.getByRole("heading", { level: 1, name: /Gate Contributor/ })),
    "the cabinet opens with the contributor's name as its heading, and the heading has the focus");
  check(await page.evaluate(() => document.activeElement?.tagName) === "H1", "the focus is on the heading");
  const content = await page.content();
  check(!content.includes("gate.maker@example.org"), "R-1401: the profile never shows the email");
  const stat = async (name) => page.locator("dl div", { has: page.locator("dt", { hasText: name }) }).locator("dd")
    .first().textContent();
  check(await stat("Slides published") === "2" && await stat("Verified slides") === "1",
    "R-1402: the profile counts two published slides, one verified");
  for (const slide of [rock, mineral]) {
    const drawer = `#drawer-${slide.node.split(".").slice(0, 2).join("-")}`;
    check(await shows(page.locator(`${drawer} [data-slide="${slide.id}"]`)),
      `R-1403: ${slide.id} lies in its collection's drawer (${drawer})`);
  }
  check(await page.locator("a[href='/api/people/me/slides.csv']").count() === 0, "a visitor is offered no export");
  await page.screenshot({ path: join(out, "cabinet-visitor.png"), fullPage: true });

  // Select both slides and print their labels on a stock.
  await page.getByRole("button", { name: "Select slides to print labels" }).click();
  for (const slide of [rock, mineral]) await page.locator(`input[data-pick="${slide.id}"]`).check();
  check(await shows(page.getByRole("status").filter({ hasText: "2 slides selected" })), "two slides are selected");
  await page.getByRole("button", { name: "Print labels" }).click();
  const dialog = page.getByRole("dialog");
  check(await shows(dialog.getByRole("combobox", { name: "Print on" })), "the print dialog opens with the stocks");
  await dialog.getByRole("combobox", { name: "Print on" }).selectOption("divbio-misl-1000");
  check(await shows(dialog.locator("[data-stock='divbio-misl-1000']").filter({ hasText: "96 on each US Letter sheet" })),
    "R-1404: the stock says its label size, grid and count per sheet");
  check(await dialog.getByText(/xylene/).count() > 0, "the stock's warnings are shown (xylene erases laser toner)");
  await dialog.getByRole("radio", { name: "Position 5, row 1, column 5" }).check();
  check(await shows(dialog.getByRole("status").filter({ hasText: "From position 5" })), "the labels start at position 5");
  await dialog.getByRole("spinbutton", { name: /Right/ }).fill("0.5");
  await dialog.getByRole("spinbutton", { name: /Down/ }).fill("-0.3");
  await page.screenshot({ path: join(out, "print-dialog.png"), fullPage: false });

  const sheetLink = dialog.locator("a[data-print=sheet]");
  const href = await sheetLink.getAttribute("href");
  const q = new URL(href, ORIGIN).searchParams;
  check(q.get("stock") === "divbio-misl-1000" && q.get("slides") === `${rock.id},${mineral.id}` && q.get("start") === "4"
    && q.get("dx") === "0.5" && q.get("dy") === "-0.3" && q.get("lang") === "en",
    `the sheet's address carries the stock, both slides, the start and the offset (${q})`);
  // Headless Chromium has no PDF viewer and hands the sheet over as a download at once, so the new tab is judged by
  // the navigation it makes, listened for before the click.
  const navigated = page.context().waitForEvent("request", { timeout: 15_000,
    predicate: (r) => r.isNavigationRequest() && new URL(r.url()).pathname === "/api/labels/sheet.pdf" })
    .catch(() => null);
  const popup = page.waitForEvent("popup");
  await sheetLink.click();
  const opened = await popup;
  const request = await navigated;
  check(request !== null && request.url().endsWith(href),
    `Print opens the sheet in a new tab (${request ? request.url() : "no navigation to the sheet"})`);
  await opened.close();
  const sheet = await pdfAt(page, href);
  check(sheet.status === 200 && sheet.type === "application/pdf" && sheet.pdf && sheet.pages === 1,
    `R-1405: the sheet is a one-page PDF (${sheet.status}, ${sheet.type}, ${sheet.pages} pages)`);
  const testHref = await dialog.locator("a[data-print=test]").getAttribute("href");
  const test = await pdfAt(page, testHref);
  check(test.status === 200 && test.pdf && test.pages === 1 && test.disposition.includes("laminario-test-divbio-misl-1000"),
    "R-1406: the test page is the stock's, a one-page PDF");

  // The offset is the printer's: kept on the device for this stock.
  await dialog.getByRole("button", { name: "Close" }).click();
  await page.getByRole("button", { name: "Print labels" }).click();
  const dx = dialog.getByRole("spinbutton", { name: /Right/ });
  check(await dialog.getByRole("combobox", { name: "Print on" }).inputValue() === "divbio-misl-1000"
    && await dx.inputValue() === "0.5", "reopened, the dialog keeps the stock and its offset");
  await dialog.getByRole("combobox", { name: "Print on" }).selectOption("a4-plain");
  check(await dx.inputValue() === "0", "another stock has its own offset");
  check(await dialog.getByText(/cut along the dashed lines/).count() > 0,
    "plain paper says to cut along the dashed lines");
  await dialog.getByRole("combobox", { name: "Print on" }).selectOption("divbio-misl-1000");
  check(await dx.inputValue() === "0.5", "back on the first stock, its offset returns");
  await dialog.getByRole("button", { name: "Close" }).click();

  // The identifier's cabinet, reached from the slide's identifications.
  await page.goto(`${ORIGIN}/s/${rock.id}`, { waitUntil: "networkidle" });
  const byOne = page.locator(`a[href="/people/${one}"]`);
  check(await shows(byOne), "each identification links its account's cabinet");
  await byOne.first().click();
  await page.waitForURL(`${ORIGIN}/people/${one}`);
  await page.getByRole("tab", { name: /Identifications/ }).click();
  const ident = page.locator(`[data-identification="${agreed.json.id}"]`);
  check(await shows(ident), "R-1403: the identifier's cabinet lists the identification");
  check(await ident.locator("dd[data-community=true]").count() === 1, "and says the community agrees with it now");
  check(new URL(page.url()).search === "?tab=identifications", "the tab is in the address");
  await page.screenshot({ path: join(out, "cabinet-identifications.png"), fullPage: true });

  // The public answers never carry the obscured slide's exact place.
  const publicRecord = await api("", "GET", `/api/slides/${rock.id}`);
  check(publicRecord.json.place.geoprivacy === "obscured" && !publicRecord.text.includes(String(EXACT.lat)),
    "the public record carries the obscured point only");
  check((await api("", "GET", "/api/people/me/slides.csv")).status === 401, "R-1407: no one exports without signing in");
  await visitor.close();

  // The contributor, signed in: the account menu leads to their cabinet, which offers the export.
  const own = await newContext();
  const mine = await own.newPage();
  await mine.goto(`${ORIGIN}/signin?next=/`, { waitUntil: "networkidle" });
  await mine.getByLabel("Email address").fill(PEOPLE.maker.email);
  await mine.getByLabel("Password").fill(PASSWORD);
  await mine.locator("form").getByRole("button", { name: "Sign in" }).click();
  await mine.waitForURL(`${ORIGIN}/`);
  await mine.getByRole("button", { name: /Gate Contributor/ }).click();
  await mine.getByRole("link", { name: "My cabinet" }).click();
  await mine.waitForURL(`${ORIGIN}/people/${maker}`);
  const exportLink = mine.getByRole("link", { name: "Export my slides (CSV)" });
  check(await shows(exportLink), "the account menu leads to the cabinet, which offers its owner the export");
  const csv = await mine.request.get(`${ORIGIN}/api/people/me/slides.csv`);
  const rows = parseCsv(await csv.text());
  const header = rows[0];
  const line = rows.slice(1).find((r) => r[0] === rock.id) ?? [];
  check(csv.status() === 200 && rows.length === 3, `R-1407: the export holds the two slides (${rows.length - 1} rows)`);
  check(Number(line[header.indexOf("latitude")]) === EXACT.lat && Number(line[header.indexOf("longitude")]) === EXACT.lon,
    "R-1407: with the obscured slide's exact place");
  await mine.screenshot({ path: join(out, "cabinet-own.png"), fullPage: true });
  const ownState = await own.storageState();
  await own.close();

  // R-080: the cabinet, the identifications and the print dialog fit at every width, room and language.
  for (const width of WIDTHS) for (const room of ROOMS) for (const lang of LANGS) {
    const tag = `${width}-${room}-${lang}`;
    const ctx = await newContext(width, room, lang, ownState);
    const p = await ctx.newPage();
    await p.goto(`${ORIGIN}/people/${maker}`, { waitUntil: "networkidle" });
    await p.evaluate(() => document.fonts.ready);
    await p.locator(`[data-slide="${mineral.id}"]`).waitFor();
    let extra = await overflow(p);
    check(extra <= 0, `the cabinet fits at ${tag} (${extra} px sideways)`);
    await p.screenshot({ path: join(out, `fit-${tag}-cabinet.png`), fullPage: true });

    await p.getByRole("button", { name: lang === "en" ? "Select slides to print labels"
      : "Elegir láminas para imprimir etiquetas" }).click();
    for (const slide of [rock, mineral]) await p.locator(`input[data-pick="${slide.id}"]`).check();
    await p.getByRole("button", { name: lang === "en" ? "Print labels" : "Imprimir etiquetas" }).click();
    await p.getByRole("dialog").locator("[data-positions]").waitFor();
    const box = await p.getByRole("dialog").evaluate((d) => ({ extra: d.scrollWidth - d.clientWidth,
      right: d.getBoundingClientRect().right, width: window.innerWidth }));
    check(box.extra <= 0 && box.right <= box.width, `the print dialog fits at ${tag} (${box.extra} px inside)`);
    await p.screenshot({ path: join(out, `fit-${tag}-print.png`), fullPage: false });
    await p.keyboard.press("Escape");

    await p.goto(`${ORIGIN}/people/${one}?tab=identifications`, { waitUntil: "networkidle" });
    await p.locator(`[data-identification="${agreed.json.id}"]`).waitFor();
    extra = await overflow(p);
    check(extra <= 0, `the identifications fit at ${tag} (${extra} px sideways)`);
    await p.screenshot({ path: join(out, `fit-${tag}-identifications.png`), fullPage: true });
    await ctx.close();
  }

  // R-085: with reduced motion, nothing on the cabinet or in the dialog moves longer than 0 ms but opacity fades.
  for (const room of ROOMS) {
    const ctx = await newContext(1280, room, "en", ownState);
    const p = await ctx.newPage();
    await p.goto(`${ORIGIN}/people/${maker}`, { waitUntil: "networkidle" });
    await p.getByRole("button", { name: "Select slides to print labels" }).click();
    await p.locator(`input[data-pick="${rock.id}"]`).check();
    await p.getByRole("button", { name: "Print labels" }).click();
    await p.getByRole("dialog").locator("[data-positions]").waitFor();
    const moving = await p.evaluate(() => {
      const ms = (v) => Math.max(...v.split(",").map((x) => (x.trim().endsWith("ms") ? parseFloat(x)
        : parseFloat(x) * 1000)));
      const bad = [];
      for (const el of document.querySelectorAll("*")) {
        for (const pseudo of [null, "::before", "::after"]) {
          const s = getComputedStyle(el, pseudo);
          const transition = ms(s.transitionDuration);
          const animation = s.animationName !== "none" ? ms(s.animationDuration) : 0;
          const onlyOpacity = s.transitionProperty.split(",").every((x) => x.trim() === "opacity");
          if (animation > 0 || (transition > 0 && !(onlyOpacity && transition <= 150))) {
            bad.push(`${el.tagName.toLowerCase()}${pseudo ?? ""}.${String(el.className).split(" ")[0]}`);
          }
        }
      }
      return bad;
    });
    check(moving.length === 0, `R-085: nothing moves with reduced motion (${room}${moving.length ? `: ${moving
      .slice(0, 5).join(", ")}` : ""})`);
    await ctx.close();
  }
} catch (error) {
  const now = Date.now();
  const waiting = [...pending].filter(([, at]) => now - at > 2000)
    .map(([r, at]) => `${r.method()} ${new URL(r.url()).pathname} (${Math.round((now - at) / 1000)} s)`);
  failures.push(`the walk stopped: ${error instanceof Error ? error.message : String(error)}` +
    (waiting.length ? `; still pending: ${waiting.slice(0, 10).join(", ")}` : "; no request pending"));
} finally {
  await browser?.close();
  await sb.stop();
}

for (const p of passed) console.log(`ok    ${p}`);
for (const f of failures) console.error(`FAIL  ${f}`);
console.log(`cabinet: ${passed.length} passed, ${failures.length} failed (sandbox ${sb.sandbox}; screenshots in ${out})`);
if (!failures.length) sb.clean();
process.exit(failures.length ? 1 : 0);
