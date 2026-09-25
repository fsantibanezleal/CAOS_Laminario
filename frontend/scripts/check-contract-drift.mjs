#!/usr/bin/env node
// The committed TypeScript contract types must equal what the committed JSON Schemas generate (R-007).
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { OUT_DIR, TARGETS, render } from "./generate-contract-types.mjs";

let stale = [];
for (const target of TARGETS) {
  const expected = await render(target);
  let actual = null;
  try {
    actual = await readFile(resolve(OUT_DIR, target.out), "utf8");
  } catch {
    actual = null;
  }
  if (actual !== expected) stale.push(target.out);
}
if (stale.length) {
  console.error(`contract types out of date: ${stale.join(", ")} (run npm run contract:generate)`);
  process.exit(1);
}
console.log("contract types: OK");
