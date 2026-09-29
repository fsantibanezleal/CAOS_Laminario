// Browser gates run against the real build: `vite preview` serves dist/ on the preview port, and each gate opens it
// with Playwright's Chromium. PLAYWRIGHT_BROWSERS_PATH names the browser cache (outside the repository).
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const FRONTEND = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const PORT = 4909;
export const ORIGIN = `http://127.0.0.1:${PORT}`;
export const WIDTHS = [360, 768, 1280, 1920];
export const ROOMS = ["daylight", "lamplit"];
export const LANGS = ["en", "es"];
export const API = "http://127.0.0.1:8147";

/**
 * Every place a visitor can open, each gate walks them all (U15 adds About). The contribute and moderation
 * places need an account; frontend/gates/contribute.mjs and identify.mjs walk them signed in, at every width, room
 * and language.
 */
export const PLACES = ["/", "/c/insects", "/c/insects/lice", "/c/rocks/igneous", "/search?q=granite",
  "/search?preparation=thin_section&node=earth.rocks", "/map", "/design", "/nowhere", "/signin", "/join",
  "/forgot-password", "/reset-password", "/identify", "/identify?badge=any", "/about", "/about#licences"];

/**
 * Slides the gates look at, found through the API (their ids belong to the collection the API serves): the first
 * slide of a drawer with a type label, one with a focal stack, one with a polarised pair, one with a single field.
 */
export async function exampleSlides() {
  const page = async (query) => (await (await fetch(`${API}/api/slides?${query}&limit=200`)).json()).items;
  const records = async (ids) => Promise.all(ids.map(async (id) => (await fetch(`${API}/api/slides/${id}`)).json()));
  const lice = await page("node=life.insects.lice");
  const rocks = await page("node=earth.rocks");
  const wsi = await page("wsi=true");
  const all = await records([...new Set([...lice.slice(0, 3), ...rocks.slice(0, 40), ...wsi].map((s) => s.id))]);
  const micro = (r) => r.assets.filter((a) => a.family === "micro" && a.status === "ready");
  const stack = all.find((r) => micro(r).some((a) => a.role === "z_plane"));
  const pair = all.find((r) => micro(r).some((a) => a.role === "polarised"));
  const single = all.find((r) => micro(r).some((a) => a.role === "single"));
  return { label: all[0], stack, pair, single, all };
}

/**
 * The places read the API through the preview's proxy. Refuse to run unless the API on 8147 is Laminario's and its
 * collection has slides: a gate against another product on the port, or an empty collection, would pass vacuously.
 * Start it with scripts/local/03_dev over a data root that holds the base collection.
 */
export async function requireApi() {
  let health;
  try {
    health = await (await fetch(`${API}/api/health`)).json();
  } catch {
    throw new Error(`no API on ${API}: start it over a data root holding the base collection (scripts/local/03_dev)`);
  }
  if (health.product !== "laminario") throw new Error(`the API on ${API} is ${health.product}, not Laminario`);
  const tree = await (await fetch(`${API}/api/collections`)).json();
  const slides = tree.realms.reduce((n, r) => n + (r.slide_count ?? 0), 0);
  if (slides < 300) throw new Error(`the API's collection holds ${slides} slides; the gates need the base collection`);
  return { version: health.version, slides };
}

/** Where a gate writes its screenshots and reports (ignored by git). */
export function outDir(gate) {
  const folder = join(FRONTEND, ".gates", gate);
  mkdirSync(folder, { recursive: true });
  return folder;
}

/** Start `vite preview` and resolve when it answers; the returned function stops it. */
export async function serve() {
  const child = spawn(process.execPath, [join(FRONTEND, "node_modules", "vite", "bin", "vite.js"), "preview", "--host",
    "127.0.0.1", "--port", String(PORT), "--strictPort"], { cwd: FRONTEND, stdio: "ignore" });
  const deadline = Date.now() + 30_000;
  for (;;) {
    try {
      const r = await fetch(`${ORIGIN}/`);
      if (r.ok) break;
    } catch {
      // not up yet
    }
    if (Date.now() > deadline) {
      child.kill();
      throw new Error("vite preview did not answer within 30 s (is dist/ built?)");
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  return () => new Promise((resolve) => {
    child.once("exit", resolve);
    child.kill();
  });
}

/** A page with the room and the language set the way a returning visitor's device has them. */
export async function openPlace(browser, path, { width, room, lang, reducedMotion = "no-preference" }) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion,
    colorScheme: room === "lamplit" ? "dark" : "light" });
  await context.addInitScript(([r, l]) => {
    try {
      localStorage.setItem("laminario.theme", r);
      localStorage.setItem("laminario.lang", l);
    } catch {
      // ignore
    }
  }, [room, lang]);
  const page = await context.newPage();
  await page.goto(`${ORIGIN}${path}`, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  return { context, page };
}
