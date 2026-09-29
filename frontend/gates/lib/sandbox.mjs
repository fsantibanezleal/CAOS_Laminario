// A whole Laminario in a sandbox for the gates that write: a fresh data root, the API, tusd (with the production flags
// of deploy/tusd/compose.yaml) and the worker, with the preview of the built site in front of them. Accounts come from
// invitations issued on the command line, as the first admin's does in production.
//
//   LAMINARIO_TUSD_BIN   tusd v2.10.1
//   LAMINARIO_VIPS_BIN   libvips on Windows
//   LAMINARIO_PYTHON     the Python with the app's dependencies (default: the repository's .venv)
//   LAMINARIO_TEST_TMP   where the sandbox goes (default: the system's temporary folder)
//
// Ports 8147 (API), 8148 (tusd) and 4909 (preview) must be free: the preview proxies to the first two.
import { spawn, spawnSync } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { createReadStream, existsSync, mkdirSync, openSync, readFileSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { FRONTEND, ORIGIN, serve } from "./serve.mjs";

export const ROOT = join(FRONTEND, "..");
export const API = "http://127.0.0.1:8147";
export const TUS = "http://127.0.0.1:8148/files/";
export const PASSWORD = `lamina-${randomBytes(6).toString("hex")}`;

export function need(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is not set (see gates/lib/sandbox.mjs)`);
  return value;
}

async function free(port) {
  return new Promise((resolve) => {
    const probe = createServer().once("error", () => resolve(false))
      .once("listening", () => probe.close(() => resolve(true))).listen(port, "127.0.0.1");
  });
}

export const sha256 = (path) => new Promise((resolve, reject) => {
  const hash = createHash("sha256");
  createReadStream(path).on("data", (d) => hash.update(d)).on("end", () => resolve(hash.digest("hex"))).on("error", reject);
});

async function waitFor(url, { status = 200, timeout = 60_000 } = {}) {
  const deadline = Date.now() + timeout;
  for (;;) {
    try {
      const r = await fetch(url);
      if (r.status === status || (status === "any" && r.status < 500)) return r;
    } catch {
      // not up yet
    }
    if (Date.now() > deadline) throw new Error(`${url} did not answer within ${timeout / 1000} s`);
    await new Promise((r) => setTimeout(r, 300));
  }
}

/** Start the sandbox; ``stop()`` takes everything down, and ``clean()`` removes it after a passing run. */
export async function startSandbox(name) {
  const tusd = need("LAMINARIO_TUSD_BIN");
  const python = process.env.LAMINARIO_PYTHON
    ?? [join(ROOT, ".venv", "Scripts", "python.exe"), join(ROOT, ".venv", "bin", "python")].find(existsSync);
  if (!python) throw new Error("no Python with the app's dependencies: set LAMINARIO_PYTHON");
  for (const port of [8147, 8148, 4909]) {
    if (!(await free(port))) throw new Error(`port ${port} is in use: the gate needs it free (it runs its own stack)`);
  }
  const sandbox = join(process.env.LAMINARIO_TEST_TMP ?? tmpdir(), `${name}-gate-${Date.now()}`);
  const dataRoot = join(sandbox, "data");
  mkdirSync(join(dataRoot, "quarantine"), { recursive: true });
  const env = { ...process.env, LAMINARIO_DATA_ROOT: dataRoot, LAMINARIO_PUBLIC_BASE_URL: ORIGIN,
    LAMINARIO_SECRET_KEY: randomBytes(32).toString("hex"), LAMINARIO_TUSD_URL: "http://127.0.0.1:8148",
    PYTHONUTF8: "1" };
  const children = [];
  const start = (label, command, args) => {
    const log = openSync(join(sandbox, `${label}.log`), "a");
    const child = spawn(command, args, { cwd: ROOT, env, stdio: ["ignore", log, log] });
    children.push(child);
    return child;
  };
  /** An invitation link's token for ``role``, issued on the command line (the database is created and migrated). */
  const invite = (role, email) => {
    const out = spawnSync(python, ["-m", "app.accounts", "invite", "--role", role, "--email", email],
      { cwd: ROOT, env, encoding: "utf8" });
    const token = /join\?token=([\w-]+)/.exec(out.stdout ?? "")?.[1];
    if (!token) throw new Error(`the invitation was not issued: ${out.stderr}`);
    return token;
  };
  // The database first: the command line migrates it.
  const firstToken = invite("admin", "gate.admin@example.org");
  start("api", python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8147"]);
  await waitFor(`${API}/api/health`);
  start("tusd", tusd, ["-host=127.0.0.1", "-port=8148", "-base-path=/files/",
    `-upload-dir=${join(dataRoot, "quarantine")}`, "-hooks-http=http://127.0.0.1:8147/api/_internal/tus-hook",
    "-hooks-http-forward-headers=Cookie", "-hooks-enabled-events=pre-create,post-finish,post-terminate",
    "-behind-proxy", "-disable-download", "-disable-cors", "-show-greeting=false"]);
  await waitFor(TUS, { status: "any" });
  start("worker", python, ["-m", "app.worker"]);
  const stopPreview = await serve();

  const stop = async () => {
    await stopPreview();
    for (const child of children.reverse()) {
      if (child.exitCode !== null) continue;
      // The worker has a pool of processes: stop the whole tree.
      if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore" });
      else child.kill("SIGTERM");
    }
  };
  return { sandbox, dataRoot, env, python, invite, adminToken: firstToken, stop,
    clean: () => rmSync(sandbox, { recursive: true, force: true }) };
}

/** An account through the API (register from an invitation, then sign in); returns its cookie header. */
export async function member(token, email, name) {
  const registered = await fetch(`${API}/api/auth/register`, { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, email, password: PASSWORD, display_name: name }) });
  if (registered.status !== 201) throw new Error(`register ${email}: ${registered.status} ${await registered.text()}`);
  const login = await fetch(`${API}/api/auth/login`, { method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password: PASSWORD }) });
  if (login.status !== 204) throw new Error(`sign in ${email}: ${login.status}`);
  return login.headers.get("set-cookie").split(";")[0];
}

/** A file sent through tusd as the browser's Uppy sends it (one creation, one PATCH), with the account's cookie. */
export async function tusUpload(cookie, slide, asset, path, type) {
  const data = readFileSync(path);
  const b64 = (s) => Buffer.from(String(s)).toString("base64");
  const meta = [["slide", slide], ["asset", asset], ["filename", basename(path)], ["filetype", type]]
    .map(([k, v]) => `${k} ${b64(v)}`).join(",");
  const created = await fetch(TUS, { method: "POST", headers: { "Tus-Resumable": "1.0.0", "Upload-Length":
    String(data.length), "Upload-Metadata": meta, Cookie: cookie } });
  if (created.status !== 201) throw new Error(`tus create: ${created.status} ${await created.text()}`);
  const location = new URL(created.headers.get("location"), TUS);
  const at = new URL(location.pathname, TUS);
  const sent = await fetch(at, { method: "PATCH", headers: { "Tus-Resumable": "1.0.0", "Upload-Offset": "0",
    "Content-Type": "application/offset+octet-stream", Cookie: cookie }, body: data });
  if (sent.status !== 204) throw new Error(`tus patch: ${sent.status} ${await sent.text()}`);
}

/** Wait until ``check`` returns a truthy value (polled every half second), or fail after ``timeout`` ms. */
export async function until(check, timeout, what) {
  const deadline = Date.now() + timeout;
  for (;;) {
    const value = await check();
    if (value) return value;
    if (Date.now() > deadline) throw new Error(`${what}: not within ${timeout / 1000} s`);
    await new Promise((r) => setTimeout(r, 500));
  }
}
