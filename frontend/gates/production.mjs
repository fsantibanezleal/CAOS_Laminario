// What only a deployment has (U16, R-1601 to R-1606), checked against the live site:
//
//   LAMINARIO_GATE_ORIGIN=https://laminario.ml.fasl-work.com node gates/production.mjs
//
// R-1601  HTTPS only: plain HTTP redirects; the certificate is valid and has weeks left
// R-1602  the API, tusd and iipsrv are not reachable from outside; the internal routes answer 404
// R-1603  the base collection as validated: the lock's slides published, the sources the About answer counts
// R-1604  a tile twice: a miss, then a hit with the same bytes; a tile of an image no published slide holds is refused
// R-1605  hashed assets cached for a year, the index never; the app's addresses answer with the app
// R-1606  the version served equals the repository's
import { readFileSync } from "node:fs";
import { connect as tcp } from "node:net";
import { connect as tls } from "node:tls";
import { join } from "node:path";
import { FRONTEND } from "./lib/serve.mjs";

const ORIGIN = process.env.LAMINARIO_GATE_ORIGIN?.replace(/\/$/, "");
if (!ORIGIN) throw new Error("set LAMINARIO_GATE_ORIGIN to the deployed site (https://laminario.ml.fasl-work.com)");
const host = new URL(ORIGIN).hostname;
const failures = [];
const passed = [];
const check = (ok, what) => (ok ? passed : failures).push(what);
const get = (path, init = {}) => fetch(`${ORIGIN}${path}`, { redirect: "manual", ...init });

// R-1601
{
  const plain = await fetch(`http://${host}/c/insects`, { redirect: "manual" });
  check(plain.status === 301 && plain.headers.get("location") === `https://${host}/c/insects`,
    `R-1601: plain HTTP redirects to HTTPS (${plain.status} ${plain.headers.get("location")})`);
  const cert = await new Promise((resolve, reject) => {
    const socket = tls({ host, port: 443, servername: host }, () => {
      const peer = socket.getPeerCertificate();
      socket.end();
      resolve({ authorized: socket.authorized, validTo: new Date(peer.valid_to), subject: peer.subject?.CN });
    });
    socket.on("error", reject);
  });
  const days = Math.round((cert.validTo - Date.now()) / 86_400_000);
  check(cert.authorized && cert.subject === host && days > 14,
    `R-1601: the certificate is trusted, names ${cert.subject}, and has ${days} days left`);
  const hsts = (await get("/")).headers.get("strict-transport-security");
  check(Boolean(hsts), `R-1601: the pages carry HSTS (${hsts})`);
}

// R-1602
{
  const closed = async (port) => new Promise((resolve) => {
    const socket = tcp({ host, port, timeout: 5000 });
    socket.on("connect", () => { socket.destroy(); resolve(false); });
    socket.on("timeout", () => { socket.destroy(); resolve(true); });
    socket.on("error", () => resolve(true));
  });
  for (const port of [8147, 8148, 8149]) check(await closed(port), `R-1602: port ${port} is not reachable from outside`);
  for (const path of ["/api/_internal/iiif-access/x", "/api/_internal/tus-hook"]) {
    const r = await get(path, { method: path.endsWith("hook") ? "POST" : "GET" });
    check(r.status === 404, `R-1602: ${path} answers ${r.status} from outside`);
  }
}

// R-1603
{
  const lock = readFileSync(join(FRONTEND, "..", "data", "base", "lock.yaml"), "utf8");
  const lockSlides = (lock.match(/^- id: /gm) ?? []).length;
  const about = await (await get("/api/about")).json();
  check(about.numbers.by_origin.base === lockSlides,
    `R-1603: the ${lockSlides} slides of the lock are published (${about.numbers.by_origin.base} base slides served)`);
  const ids = about.sources.map((s) => s.id).sort().join(",");
  check(ids.split(",").every((id) => id !== "other") && about.sources.length >= 5,
    `R-1603: every image comes from a known source (${ids})`);
  check(about.numbers.wsi >= 14, `R-1603: ${about.numbers.wsi} whole-slide scans`);
  check(about.numbers.countries > 0, `R-1603: ${about.numbers.countries} countries stated by the sources`);
}

// R-1604
{
  const page = await (await get("/api/slides?wsi=true&limit=5")).json();
  let tile = null;
  for (const summary of page.items) {
    const record = await (await get(`/api/slides/${summary.id}`)).json();
    const asset = record.assets.find((a) => a.family === "micro" && a.status === "ready" && a.iiif_info_url);
    if (!asset) continue;
    const info = await (await get(new URL(asset.iiif_info_url).pathname)).json();
    tile = `${new URL(info.id).pathname}/0,0,512,512/512,/0/default.jpg`;
    break;
  }
  check(tile !== null, "R-1604: a whole-slide image with a IIIF service to read tiles from");
  if (tile) {
    // A fresh tile each run: the cache key is the address, so a size the viewer never asks for starts cold.
    const cold = tile.replace("/512,/", `/${500 + Math.floor(Math.random() * 12)},/`);
    const first = await get(cold);
    const a = Buffer.from(await first.arrayBuffer());
    const second = await get(cold);
    const b = Buffer.from(await second.arrayBuffer());
    check(first.status === 200 && first.headers.get("x-cache-status") === "MISS",
      `R-1604: the first request of a tile is a miss (${first.status} ${first.headers.get("x-cache-status")})`);
    check(second.headers.get("x-cache-status") === "HIT" && a.equals(b) && a.length > 1000,
      `R-1604: the second is a hit with the same ${a.length} bytes`);
  }
  const refused = await get("/iiif/ZZZZZZZZ%2F1-000000000000.tif/0,0,256,256/256,/0/default.jpg");
  check(refused.status === 403, `R-1604: a tile of an image no published slide holds is refused (${refused.status})`);
}

// R-1605
{
  const index = await get("/");
  const html = await index.text();
  check(/no-cache/.test(index.headers.get("cache-control") ?? ""), `R-1605: the index is never cached (${index.headers.get("cache-control")})`);
  const asset = /\/assets\/[^"]+\.js/.exec(html)?.[0];
  const js = asset ? await get(asset) : null;
  check(Boolean(js) && /max-age=31536000/.test(js.headers.get("cache-control") ?? ""),
    `R-1605: a hashed asset is cached for a year (${js?.headers.get("cache-control")})`);
  for (const path of ["/c/insects", "/about", "/s/ZZZZZZZZ"]) {
    const r = await get(path);
    const body = await r.text();
    check(r.status === 200 && body.includes('<div id="root">'), `R-1605: ${path} answers with the app (${r.status})`);
  }
}

// R-1606
{
  const expected = readFileSync(join(FRONTEND, "..", "VERSION"), "utf8").trim();
  const health = await (await get("/api/health")).json();
  check(health.product === "laminario" && health.version === expected,
    `R-1606: the site serves ${health.version}, the repository's ${expected}`);
}

for (const p of passed) console.log(`ok    ${p}`);
for (const f of failures) console.error(`FAIL  ${f}`);
console.log(`production: ${passed.length} passed, ${failures.length} failed against ${ORIGIN}`);
process.exit(failures.length ? 1 : 0);
