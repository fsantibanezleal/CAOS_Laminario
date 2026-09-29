// R-1308 end to end in the browser, in its own sandbox (gates/lib/sandbox.mjs): a contributor's slide is published
// (through the API and tusd: the contribute gate walks that part in the browser), two identifiers agree with its
// anchor from the Identify place and the slide becomes verified; a curator hides it with a reason, a visitor no
// longer finds it and its contributor sees why; the curator restores it from the moderation place and it is back.
// Then the Identify place, the moderation place and the slide's identifications fit at every width, room and language
// (R-080).
//
// The case pairs two real files: a scan of a thin section of the Siilinjarvi apatite ore, a carbonatite (Wikimedia
// Commons, "Thin section scan crossed polarizers Siilinjärvi R636-116.75.jpg", by kallerna, CC BY-SA 4.0; 6400 dpi,
// 3.97 um per pixel, from the file's own resolution tag), and a photograph of a place (the contribute gate's). They
// are put together only for this gate.
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

const out = outDir("identify");
const sb = await startSandbox("identify");
let browser = null;

const PEOPLE = {
  maker: { role: "contributor", email: "gate.maker@example.org", name: "Gate Contributor" },
  one: { role: "identifier", email: "gate.one@example.org", name: "Gate Identifier One" },
  two: { role: "identifier", email: "gate.two@example.org", name: "Gate Identifier Two" },
  curator: { role: "curator", email: "gate.curator@example.org", name: "Gate Curator" },
};

async function api(cookie, method, path, body) {
  const r = await fetch(`${API}${path}`, { method, headers: { Cookie: cookie,
    ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
  const text = await r.text();
  return { status: r.status, json: text ? JSON.parse(text) : null };
}

async function signIn(context, who) {
  const page = await context.newPage();
  await page.goto(`${ORIGIN}/signin?next=/identify`, { waitUntil: "networkidle" });
  await page.getByLabel("Email address").fill(who.email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.locator("form").getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(`${ORIGIN}/identify`);
  return page;
}

async function newContext(width = 1280, room = "daylight", lang = "en", storageState = undefined) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: "reduce",
    colorScheme: room === "lamplit" ? "dark" : "light", storageState });
  await context.addInitScript(([r, l]) => {
    try { localStorage.setItem("laminario.theme", r); localStorage.setItem("laminario.lang", l); } catch { /* */ }
  }, [room, lang]);
  return context;
}

try {
  const cookies = {};
  for (const [key, who] of Object.entries(PEOPLE)) {
    cookies[key] = await member(sb.invite(who.role, who.email), who.email, who.name);
  }

  // The contributor's slide, through the API and tusd.
  const anchor = { kind: "rock", ref: "carbonatite", name: "Carbonatite" };
  const placed = await api(cookies.maker, "POST", "/api/placement", { anchor });
  const node = placed.json.suggestion;
  const created = await api(cookies.maker, "POST", "/api/slide-cases", {
    slide: { format: "petro_27x46", coverslip: "none", preparation: "thin_section", catalogue_number: "R636-116.75" },
    specimen: { anchor, locality_text: "Siilinjärvi apatite mine, Finland", country: "FI", geoprivacy: "open" },
    placement: { node },
    assets: [
      { family: "macro", role: "place", upload_id: "gate-photo-0001", creator: "Mulatoenchile (Wikimedia Commons)",
        licence: "https://creativecommons.org/licenses/by-sa/3.0/" },
      { family: "micro", role: "single", upload_id: "gate-scan-00001", creator: "kallerna (Wikimedia Commons)",
        licence: "https://creativecommons.org/licenses/by-sa/4.0/", pixel_size_um: 3.97, modality: "polarised_xpl" },
    ],
  });
  if (created.status !== 201) throw new Error(`the case: ${created.status} ${JSON.stringify(created.json)}`);
  const id = created.json.id;
  const draft = await api(cookies.maker, "GET", `/api/slide-cases/${id}`);
  for (const image of draft.json.images) {
    const file = image.family === "macro" ? PHOTO : SCAN;
    await tusUpload(cookies.maker, id, image.asset_id, file, "image/jpeg");
  }
  await until(async () => (await api(cookies.maker, "GET", `/api/slide-cases/${id}`)).json.images
    .every((i) => i.has_file), 240_000, "both files accepted");
  const submitted = await api(cookies.maker, "POST", `/api/slide-cases/${id}/submit`);
  if (submitted.status !== 200) throw new Error(`submit: ${submitted.status}`);
  await until(async () => (await api(cookies.maker, "GET", `/api/slide-cases/${id}`)).json.status === "published",
    300_000, "the slide published");
  check(true, `the slide ${id} published (a carbonatite thin section in ${node})`);

  browser = await chromium.launch();

  // Two identifiers agree from the Identify place (R-1308).
  for (const key of ["one", "two"]) {
    const context = await newContext();
    const page = await signIn(context, PEOPLE[key]);
    const card = page.locator(`[data-slide="${id}"]`);
    if (key === "one") check(await shows(card), "R-1307: the slide waits in the Identify queue");
    await page.goto(`${ORIGIN}/s/${id}`, { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Identifications" }).scrollIntoViewIfNeeded();
    await page.locator("label", { has: page.locator("input[type=radio][value=rock]") }).first().click();
    await page.getByRole("combobox", { name: "The rock" }).fill("carbonat");
    await page.getByRole("option", { name: /^carbonatite/i }).first().click();
    await page.getByRole("textbox", { name: "Comment", exact: true }).fill(
      key === "one" ? "Calcite with apatite and phlogopite." : "Agreed.");
    await page.getByRole("button", { name: "Add the identification" }).click();
    await shows(page.getByText("Your identification is added."));
    if (key === "one") {
      check(await shows(page.locator("[data-badge=verified]")),
        "the contributor and one identifier agree: the slide is verified");
      check(await shows(page.locator('[class*="quality"][data-badge=verified]')),
        "the slide's record says so at once, without a reload");
      await page.screenshot({ path: join(out, "verified.png"), fullPage: true });
    }
    await context.close();
  }
  const listed = await api("", "GET", `/api/slides/${id}/identifications`);
  check(listed.json.community.badge === "verified" && listed.json.identifications.length === 3,
    "R-1308: two identifiers agree with the contributor's anchor, and the slide is verified");
  check(listed.json.community.score === 1, "every identification supports the community anchor");

  // A curator hides it with a reason.
  const curatorContext = await newContext();
  const curator = await signIn(curatorContext, PEOPLE.curator);
  await curator.goto(`${ORIGIN}/s/${id}`, { waitUntil: "networkidle" });
  await curator.getByRole("button", { name: "Hide this slide" }).click();
  await curator.getByRole("dialog").getByRole("textbox", { name: "Reason" })
    .fill("The two images are of different specimens; checking with the contributor.");
  await curator.getByRole("dialog").getByRole("button", { name: "Hide" }).click();
  await curator.waitForURL(`${ORIGIN}/moderate`);
  check(true, "the curator hid the slide, and was taken to the moderation place");

  const visitor = await newContext();
  const vpage = await visitor.newPage();
  const gone = await vpage.goto(`${ORIGIN}/api/slides/${id}`);
  check(gone.status() === 404, "R-1306: a visitor no longer finds the slide");
  await vpage.goto(`${ORIGIN}/search?q=carbonatite`, { waitUntil: "networkidle" });
  check(await vpage.locator(`[data-slide="${id}"]`).count() === 0, "search no longer lists it");
  const makerCase = await api(cookies.maker, "GET", "/api/slide-cases");
  const hiddenCase = makerCase.json.find((c) => c.id === id);
  check(hiddenCase?.status === "hidden" && /different specimens/.test(hiddenCase.status_reason ?? ""),
    "R-1306: its contributor sees why");

  // Restored from the moderation place.
  await curator.getByRole("tab", { name: /^Hidden/ }).click();
  await curator.getByRole("tabpanel").getByRole("button", { name: "Restore" }).first().click();
  await curator.getByRole("dialog").getByRole("textbox", { name: "Reason" })
    .fill("The contributor confirmed both images are of R636-116.75.");
  await curator.getByRole("dialog").getByRole("button", { name: "Restore" }).click();
  await shows(curator.getByText("It is restored."));
  const back = await vpage.goto(`${ORIGIN}/api/slides/${id}`);
  check(back.status() === 200, "R-1308: restored by the curator, the slide is back for a visitor");
  const log = await api(cookies.curator, "GET", `/api/moderation/actions?slide=${id}`);
  check(log.json.map((a) => a.action).join(",") === "unhide,hide", "both actions are in the log, with their reasons");
  await curator.screenshot({ path: join(out, "moderate.png"), fullPage: true });
  const curatorState = await curatorContext.storageState();
  await curatorContext.close();
  await visitor.close();

  // The places fit (R-080): the queue, the moderation place and the slide's identifications.
  const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  for (const width of WIDTHS) for (const room of ROOMS) for (const lang of LANGS) {
    const tag = `${width}-${room}-${lang}`;
    const ctx = await newContext(width, room, lang, curatorState);
    const p = await ctx.newPage();
    for (const [path, name] of [["/identify?badge=any", "identify"], ["/moderate", "moderate"], [`/s/${id}`, "slide"]]) {
      await p.goto(`${ORIGIN}${path}`, { waitUntil: "networkidle" });
      await p.evaluate(() => document.fonts.ready);
      if (name === "slide") await p.getByRole("heading", { name: /Identifications|Identificaciones/ }).waitFor();
      const extra = await overflow(p);
      check(extra <= 0, `${path} fits at ${tag} (${extra} px sideways)`);
      await p.screenshot({ path: join(out, `fit-${tag}-${name}.png`), fullPage: true });
    }
    await ctx.close();
  }
} catch (error) {
  failures.push(`the walk stopped: ${error instanceof Error ? error.message : String(error)}`);
} finally {
  await browser?.close();
  await sb.stop();
}

for (const p of passed) console.log(`ok    ${p}`);
for (const f of failures) console.error(`FAIL  ${f}`);
console.log(`identify: ${passed.length} passed, ${failures.length} failed (sandbox ${sb.sandbox}; screenshots in ${out})`);
if (!failures.length) sb.clean();
process.exit(failures.length ? 1 : 0);
