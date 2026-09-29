// R-1505: every external link the About place shows answers, or is listed as not checkable by a machine. The links
// are read from the content's sources (src/about/content.en.ts, content.es.ts: every `href: "..."`) and from
// app/about/credits.json (every url, terms and DOI). Three outcomes (dossier 17, section 8):
//
//   reachable     the address answers 2xx after redirects (HEAD, else GET)
//   unverifiable  a bot challenge answers instead (Cloudflare's "Just a moment...", cf-mitigated), for a person to open
//   broken        anything else: 4xx or 5xx without a challenge, a DNS failure, a timeout
//
// It needs the network, so it runs before a release, not in continuous integration (ADR-0074). Only broken fails.
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { FRONTEND, outDir } from "./lib/serve.mjs";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36 "
  + "Laminario-link-check";
const links = new Set();
for (const file of ["src/about/content.en.ts", "src/about/content.es.ts"]) {
  for (const m of readFileSync(join(FRONTEND, file), "utf8").matchAll(/href: "(https?:\/\/[^"]+)"/g)) links.add(m[1]);
}
const credits = JSON.parse(readFileSync(join(FRONTEND, "..", "app", "about", "credits.json"), "utf8"));
for (const group of ["sources", "vocabularies", "map", "software", "fonts"]) {
  for (const item of credits[group]) {
    for (const url of [item.url, item.terms, item.doi ? `https://doi.org/${item.doi}` : null]) if (url) links.add(url);
  }
}

async function probe(url) {
  // A DOI's landing page is the publisher's, often behind a challenge; doi.org's handle API says whether the DOI is
  // registered, which is what the link promises.
  const doi = /^https:\/\/doi\.org\/(10\..+)$/.exec(url);
  if (doi) {
    try {
      const r = await fetch(`https://doi.org/api/handles/${doi[1]}`, { signal: AbortSignal.timeout(30_000) });
      const body = r.ok ? await r.json() : null;
      if (body?.responseCode === 1) return { outcome: "reachable", status: "DOI registered" };
      return { outcome: "broken", status: `DOI ${body?.responseCode ?? r.status}` };
    } catch (error) {
      return { outcome: "broken", status: error.message };
    }
  }
  for (const method of ["HEAD", "GET"]) {
    try {
      const r = await fetch(url, { method, redirect: "follow", headers: { "User-Agent": UA },
        signal: AbortSignal.timeout(30_000) });
      const challenged = r.headers.get("cf-mitigated") === "challenge"
        || ((r.status === 403 || r.status === 503) && method === "GET"
          && /Just a moment|challenge-platform|cf-chl/i.test(await r.text()));
      if (challenged) return { outcome: "unverifiable", status: r.status };
      if (r.ok) return { outcome: "reachable", status: r.status };
      if (method === "GET") return { outcome: "broken", status: r.status };
    } catch (error) {
      if (method === "GET") return { outcome: "broken", status: error.name === "TimeoutError" ? "timeout" : error.message };
    }
  }
  return { outcome: "broken", status: "unknown" };
}

const results = [];
for (const url of [...links].sort()) results.push({ url, ...(await probe(url)) });
const by = (o) => results.filter((r) => r.outcome === o);
for (const r of by("broken")) console.error(`BROKEN        ${r.status}  ${r.url}`);
for (const r of by("unverifiable")) console.log(`UNVERIFIABLE  ${r.status}  ${r.url}  (open it in a browser)`);
const report = join(outDir("links"), "links.json");
writeFileSync(report, JSON.stringify(results, null, 1));
console.log(`links: ${results.length} checked, ${by("reachable").length} reachable, ${by("unverifiable").length} not `
  + `checkable by a machine, ${by("broken").length} broken; the list in ${report}`);
process.exit(by("broken").length ? 1 : 0);
