// R-081: every declared foreground and background pair of both rooms reaches its WCAG 2.2 contrast minimum (4.5:1
// for text, 3:1 for component boundaries and the focus ring). Reads src/design/tokens.json, the same source the
// stylesheet is generated from, and prints every pair with its ratio.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { contrast, resolveRoom } from "./lib/color.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const tokens = JSON.parse(readFileSync(join(here, "..", "src", "design", "tokens.json"), "utf8"));

let failures = 0;
let checked = 0;
for (const room of Object.keys(tokens.rooms)) {
  const { colours, hues } = resolveRoom(tokens, room);
  for (const [group, pair] of Object.entries(tokens.pairs)) {
    const foregrounds = pair.foregrounds.flatMap((f) =>
      f === "hue:*" ? Object.keys(hues).map((k) => [`hue ${k}`, hues[k]]) : [[f, colours[f]]]);
    for (const [fgName, fg] of foregrounds) {
      for (const bgName of pair.backgrounds) {
        if (!fg || !colours[bgName]) {
          console.error(`${room}: unknown token in pair ${group}: ${fgName} on ${bgName}`);
          failures += 1;
          continue;
        }
        const ratio = contrast(fg, colours[bgName]);
        checked += 1;
        const ok = ratio >= pair.minimum;
        if (!ok) failures += 1;
        if (!ok || process.argv.includes("--verbose")) {
          console.log(`${ok ? "pass" : "FAIL"} ${room} ${group}: ${fgName} ${fg} on ${bgName} ${colours[bgName]} ` +
            `${ratio.toFixed(2)} (minimum ${pair.minimum})`);
        }
      }
    }
  }
}
console.log(`contrast: ${checked} pairs checked, ${failures} below their minimum`);
process.exit(failures ? 1 : 0);
