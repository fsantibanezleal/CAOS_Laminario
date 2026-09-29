// R-087, R-1201 and R-1208, end to end in the browser, on real files. The gate builds its own sandbox: a fresh data
// root, the API, the worker and tusd (the upload server) wired as in production, and the preview of the built site in
// front of them. Then a contributor is invited from the command line, joins from the link, signs out and in again,
// and fills a slide case by pointer: a scanner file (CMU-1, an Aperio SVS of 178 MB) and a photograph carrying its
// GPS position, in a private case. The page shows the position, the file leaves without it, the server verifies and
// processes both, the case is published, and the slide opens at its address with each file's SHA-256.
//
//   LAMINARIO_FIXTURES   the data vault (samples/cmu1.svs, samples/commons_san_cristobal_gps.jpg)
//
// and the sandbox's own variables and ports (gates/lib/sandbox.mjs).
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";
import exifr from "exifr";
import { chromium } from "playwright";
import { need, PASSWORD, sha256, startSandbox } from "./lib/sandbox.mjs";
import { LANGS, ORIGIN, ROOMS, WIDTHS, outDir } from "./lib/serve.mjs";

const failures = [];
const passed = [];
const check = (ok, what) => (ok ? passed : failures).push(what);
/** Whether a locator becomes visible within ``timeout`` ms (a check must wait for the page, not race it). */
const shows = (locator, timeout = 15_000) => locator.first().waitFor({ state: "visible", timeout }).then(() => true,
  () => false);

const fixtures = need("LAMINARIO_FIXTURES");
const SCANNER = join(fixtures, "samples", "cmu1.svs");
const PHOTO = join(fixtures, "samples", "commons_san_cristobal_gps.jpg");
for (const file of [SCANNER, PHOTO]) if (!existsSync(file)) throw new Error(`missing fixture ${file}`);

const out = outDir("contribute");
const EMAIL = "gate.contributor@example.org";
const NAME = "Gate Contributor";
const sb = await startSandbox("contribute");
const { sandbox, dataRoot } = sb;
let browser = null;

try {
  const token = sb.invite("contributor", EMAIL);
  browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: "en-GB" });
  await context.addInitScript(() => {
    try { localStorage.setItem("laminario.lang", "en"); } catch { /* ignore */ }
  });
  const page = await context.newPage();
  page.setDefaultTimeout(30_000);

  // R-1201: join from the invitation link, then sign out and sign in again.
  await page.goto(`${ORIGIN}/join?token=${token}`, { waitUntil: "networkidle" });
  await page.getByLabel("Your name").fill(NAME);
  await page.getByLabel("Email address").fill(EMAIL);
  await page.getByLabel("New password").fill(PASSWORD);
  await page.getByLabel("The password again").fill(PASSWORD);
  await page.getByRole("button", { name: "Open my account" }).click();
  await page.waitForURL(`${ORIGIN}/contribute`);
  check(await shows(page.getByRole("button", { name: NAME })), "R-1201: joined from the invitation, and the masthead names the account");
  await page.getByRole("button", { name: NAME }).click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.waitForURL(/\/$|\/signin/);
  check(await shows(page.getByRole("link", { name: "Sign in" })), "R-1201: signed out");
  await page.goto(`${ORIGIN}/signin?next=/contribute`, { waitUntil: "networkidle" });
  await page.getByLabel("Email address").fill(EMAIL);
  await page.getByLabel("Password").fill("not the password");
  await page.locator("form").getByRole("button", { name: "Sign in" }).click();
  check(await shows(page.getByRole("alert").filter({ hasText: "not right" })), "R-1201: a wrong password is refused, in words");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.locator("form").getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(`${ORIGIN}/contribute`);
  check(await shows(page.getByRole("button", { name: NAME })), "R-1201: signed in again");

  // The case, by pointer. What it shows: a mammal (CMU-1 is mammalian tissue; OpenSlide does not name the species).
  await page.getByRole("link", { name: /A new slide/ }).click();
  await page.waitForURL(`${ORIGIN}/contribute/new`);
  await page.getByRole("combobox", { name: "Its scientific name" }).fill("Mammalia");
  await page.getByRole("option", { name: /^Mammalia\b/ }).first().click();
  await page.getByRole("button", { name: /^Next: The slide/ }).click();
  await page.locator("label", { has: page.locator("input[name=preparation][value=section]") }).click();
  await page.getByRole("button", { name: /^Next: Images/ }).click();

  // The images: the photograph (shown with its position) and the scanner file.
  await page.locator("input[type=file][accept^='image/jpeg']").first().setInputFiles(PHOTO);
  await page.locator("input[type=file][accept*='.svs']").setInputFiles(SCANNER);
  const photoCard = page.locator("li[data-family=macro]");
  const position = photoCard.getByText(/Position in the photograph: -33\.4\d+, -70\.\d+/);
  await position.waitFor();
  check(await shows(position), "R-087: the photograph's position is read and shown before anything is sent");
  await photoCard.getByLabel("What it shows").selectOption("place");
  await photoCard.getByLabel("Licence").selectOption("https://creativecommons.org/licenses/by-sa/3.0/");
  await photoCard.getByLabel("Made by").fill("Mulatoenchile (Wikimedia Commons)");
  const scanCard = page.locator("li[data-family=micro]");
  check(await scanCard.getByLabel("What it shows").inputValue() === "pyramid", "a scanner file is taken as a whole-slide image");
  await scanCard.getByLabel("Licence").selectOption("https://creativecommons.org/publicdomain/zero/1.0/");
  await scanCard.getByLabel("Made by").fill("OpenSlide test data (Carnegie Mellon University)");
  await page.getByRole("button", { name: /^Next: The place/ }).click();

  // A private place: the page says the position will leave the file.
  await page.locator("label", { has: page.locator("input[name=geoprivacy][value=private]") }).click();
  check(await shows(page.getByText("Photographs with a position: 1")), "R-087: a private case says the position is removed");
  await page.getByRole("button", { name: /^Next: The drawer/ }).click();
  await page.getByText("The suggested drawer").waitFor();
  await page.screenshot({ path: join(out, "drawer.png"), fullPage: true });
  await page.getByRole("button", { name: /^Next: Review and send/ }).click();
  await page.getByText("Nothing stops the case.").waitFor({ timeout: 60_000 });
  await page.screenshot({ path: join(out, "review.png"), fullPage: true });

  // Stored, sent, verified, submitted, processed, published.
  await page.getByRole("button", { name: "Store the draft" }).click();
  await page.waitForURL(/\/contribute\/[0-9A-Z]{8}\?step=send$/);
  const id = /\/contribute\/([0-9A-Z]{8})/.exec(page.url())[1];
  await page.getByRole("button", { name: /^Send the files \(2\)/ }).click();
  await page.waitForFunction(() => document.querySelectorAll("li[data-tone=ok]").length === 2, null, { timeout: 300_000 });
  check(true, `the draft ${id}: both files sent through tus and accepted by the verification`);
  await page.screenshot({ path: join(out, "files.png"), fullPage: true });
  await page.getByRole("button", { name: "Submit for publication" }).click();
  await page.getByText("The slide " + id + " is in the collection now").waitFor({ timeout: 1_200_000 });
  check(true, "R-1208: the case was processed and published");
  await page.screenshot({ path: join(out, "published.png"), fullPage: true });

  // The stored files: the photograph without its position, the scanner file as it was.
  const sources = join(dataRoot, "sources", id);
  const stored = readdirSync(sources, { recursive: true }).map((f) => join(sources, String(f)))
    .filter((f) => statSync(f).isFile());
  const photoStored = stored.find((f) => /\.jpe?g$/i.test(f));
  const scanStored = stored.find((f) => /\.svs$/i.test(f));
  check(Boolean(photoStored && scanStored), "both originals are kept in the sandbox's sources");
  if (photoStored) {
    const gps = await exifr.gps(readFileSync(photoStored)).catch(() => undefined);
    check(!gps, "R-087: the stored photograph carries no position");
    const kept = await exifr.parse(readFileSync(photoStored), ["DateTimeOriginal"]).catch(() => undefined);
    check(Boolean(kept?.DateTimeOriginal), "R-1204: the stored photograph keeps its date");
  }
  const scanSha = await sha256(SCANNER);
  if (scanStored) check(await sha256(scanStored) === scanSha, "the scanner file is stored byte for byte");

  // The slide at its address, with the file's SHA-256.
  await page.getByRole("link", { name: "Open the slide" }).click();
  await page.waitForURL(`${ORIGIN}/s/${id}`);
  await page.locator(`[data-sha256="${scanSha}"]`).waitFor({ timeout: 30_000 }).catch(() => undefined);
  check(await page.locator(`[data-sha256="${scanSha}"]`).count() === 1,
    "R-1208: the slide opens at its address with the scanner file's SHA-256");
  await page.screenshot({ path: join(out, "slide.png"), fullPage: true });

  // The places fit (R-080): every section of the editor, the list and the account places, at every width of the
  // interface's gates, in both rooms and both languages, with no sideways scroll; each one screenshotted.
  const signedIn = await context.storageState();
  const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  for (const width of WIDTHS) for (const room of ROOMS) for (const lang of LANGS) {
    const tag = `${width}-${room}-${lang}`;
    for (const withAccount of [true, false]) {
      const ctx = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: "reduce",
        colorScheme: room === "lamplit" ? "dark" : "light", storageState: withAccount ? signedIn : undefined });
      await ctx.addInitScript(([r, l]) => {
        try { localStorage.setItem("laminario.theme", r); localStorage.setItem("laminario.lang", l); } catch { /* */ }
      }, [room, lang]);
      const p = await ctx.newPage();
      const visit = async (path, name) => {
        await p.goto(`${ORIGIN}${path}`, { waitUntil: "networkidle" });
        await p.evaluate(() => document.fonts.ready);
        const extra = await overflow(p);
        check(extra <= 0, `${path} fits at ${tag} (${extra} px sideways)`);
        await p.screenshot({ path: join(out, `fit-${tag}-${name}.png`), fullPage: true });
      };
      if (withAccount) {
        await visit("/contribute", "list");
        await visit("/contribute/new", "step-1");
        for (let step = 2; step <= 6; step += 1) {
          await p.locator("nav ol li button").nth(step - 1).click();
          await p.waitForTimeout(400);
          if (step === 4) {
            check(await shows(p.locator("[data-drawn]"), 20_000), `the place's map drew its countries at ${tag}`);
          }
          const extra = await overflow(p);
          check(extra <= 0, `the editor's section ${step} fits at ${tag} (${extra} px sideways)`);
          await p.screenshot({ path: join(out, `fit-${tag}-step-${step}.png`), fullPage: true });
        }
      } else {
        await visit("/signin", "signin");
        await visit(`/join?token=${"x".repeat(43)}`, "join");
        await visit("/forgot-password", "forgot");
        await visit(`/reset-password?token=${"x".repeat(43)}`, "reset");
      }
      await ctx.close();
    }
  }
  await context.close();
} catch (error) {
  failures.push(`the walk stopped: ${error instanceof Error ? error.message : String(error)}`);
} finally {
  await browser?.close();
  await sb.stop();
}

for (const p of passed) console.log(`ok    ${p}`);
for (const f of failures) console.error(`FAIL  ${f}`);
console.log(`contribute: ${passed.length} passed, ${failures.length} failed (sandbox ${sandbox}; screenshots in ${out})`);
if (!failures.length) sb.clean();
process.exit(failures.length ? 1 : 0);
