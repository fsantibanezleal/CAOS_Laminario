#!/usr/bin/env node
// Generate frontend/src/contract/*.ts from the committed JSON Schemas in ../contracts.
// The web imports only these types; check-contract-drift.mjs fails when they differ from the schemas.
import { compile } from "json-schema-to-typescript";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
export const ROOT = resolve(here, "..", "..");
export const OUT_DIR = resolve(here, "..", "src", "contract");

export const TARGETS = [
  { schema: "contracts/ingest.schema.json", out: "ingest.ts", name: "SlideCaseSubmission" },
  { schema: "contracts/catalog.schema.json", out: "catalog.ts", name: "LaminarioCatalog" },
];

const BANNER = (schema) =>
  `// Generated from ${schema} by frontend/scripts/generate-contract-types.mjs. Do not edit by hand;\n` +
  `// run \`npm run contract:generate\` after scripts/export_contracts.py. A drift fails the build.\n`;

export async function render(target) {
  const schema = JSON.parse(await readFile(resolve(ROOT, target.schema), "utf8"));
  const body = await compile(schema, target.name, {
    bannerComment: "",
    additionalProperties: false,
    style: { singleQuote: false, semi: true, printWidth: 110 },
  });
  return BANNER(target.schema) + body;
}

export async function generate() {
  await mkdir(OUT_DIR, { recursive: true });
  for (const target of TARGETS) {
    await writeFile(resolve(OUT_DIR, target.out), await render(target), "utf8");
    console.log(`wrote src/contract/${target.out}`);
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await generate();
}
