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
