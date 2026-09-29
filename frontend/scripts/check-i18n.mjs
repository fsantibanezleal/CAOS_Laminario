// R-089: every interface string exists in English and Spanish. Reads the two catalogues (src/i18n/en.ts, es.ts) and
// fails on a key in one and not the other, an empty value, or a value whose placeholders ({name}) differ.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const read = (lang) => {
  const text = readFileSync(join(here, "..", "src", "i18n", `${lang}.ts`), "utf8");
  const entries = new Map();
  for (const m of text.matchAll(/^\s*"([a-z0-9._\-]+)":\s*"((?:[^"\\]|\\.)*)",?\s*$/gim)) {
    if (entries.has(m[1])) throw new Error(`${lang}: ${m[1]} appears twice`);
    entries.set(m[1], m[2]);
  }
  if (entries.size === 0) throw new Error(`${lang}: no entries read`);
  return entries;
};

const placeholders = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");
const catalogues = { en: read("en"), es: read("es") };
const problems = [];
for (const [lang, other] of [["en", "es"], ["es", "en"]]) {
  for (const key of catalogues[lang].keys()) {
    if (!catalogues[other].has(key) && !(lang === "es" && key.endsWith(".many"))) {
      problems.push(`${key} is in ${lang} and not in ${other}`);
    }
  }
}
for (const [lang, entries] of Object.entries(catalogues)) {
  for (const [key, value] of entries) {
    if (!value.trim()) problems.push(`${lang}: ${key} is empty`);
  }
}
for (const [key, value] of catalogues.en) {
  const es = catalogues.es.get(key);
  if (es !== undefined && placeholders(es) !== placeholders(value)) {
    problems.push(`${key}: placeholders differ (en {${placeholders(value)}}, es {${placeholders(es)}})`);
  }
}
for (const p of problems) console.error(p);
console.log(`i18n: ${catalogues.en.size} strings in en, ${catalogues.es.size} in es, ${problems.length} problems`);
process.exit(problems.length ? 1 : 0);
