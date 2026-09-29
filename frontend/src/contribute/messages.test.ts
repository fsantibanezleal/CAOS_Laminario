// R-1202: every code the server sends has words in the interface, and an unknown code falls back to its message.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { en } from "../i18n/en";
import { es } from "../i18n/es";
import { messageKey, worded } from "./messages";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");

/** The codes the server's rules name: code="..." in the contract, the vocabulary and the tree's checks. */
function serverCodes(): Set<string> {
  const files = ["app/contracts/ingest.py", "app/collections/vocab.py", "app/collections/service.py"];
  const codes = new Set<string>();
  for (const file of files) {
    const text = readFileSync(join(root, file), "utf8");
    for (const m of text.matchAll(/code="([a-z_]+)"/g)) codes.add(m[1]);
    for (const m of text.matchAll(/Flag\("([a-z_]+)"/g)) codes.add(m[1]);
    for (const m of text.matchAll(/_error\([^)]*?"([a-z_]+)"\s*[,)]/gs)) codes.add(m[1]);
  }
  return codes;
}

describe("validation messages by code", () => {
  it("has words in both languages for every code the server names", () => {
    const codes = serverCodes();
    expect(codes.size).toBeGreaterThan(30);
    const missing = [...codes].filter((code) => !messageKey(code));
    expect(missing).toEqual([]);
    for (const code of codes) expect((es as Record<string, string>)[`validation.${code}`]).toBeTruthy();
  });

  it("fills the parameters, and falls back to the server's words for a code it does not know", () => {
    const t = (key: keyof typeof en, vars?: Record<string, string | number>) =>
      en[key].replace(/\{(\w+)\}/g, (_, name: string) => String(vars?.[name] ?? `{${name}}`));
    expect(worded(t, { code: "coverslip_too_large", message: "x", params: { width: "76", height: "26" } }))
      .toBe("The coverslip does not fit on the slide: at most 76 x 26 mm.");
    expect(worded(t, { code: "type.string_too_long", message: "x", params: { max_length: "80" } }))
      .toBe("Too long: at most 80 characters.");
    expect(worded(t, { code: "something_new", message: "the server says so" })).toBe("the server says so");
    expect(worded(t, { code: null, message: "no code" })).toBe("no code");
  });
});
