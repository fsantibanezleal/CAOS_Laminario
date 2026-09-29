// R-1502, R-1504, R-1507: the About content says the same in both languages (sections, blocks, equations, figures,
// links), describes every source of app/about/credits.json and every licence family the policy accepts, and every
// equation typesets.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import katex from "katex";
import { describe, expect, it } from "vitest";
import { aboutEn } from "./content.en";
import { aboutEs } from "./content.es";
import type { AboutContent, Block, Inline, LicenceFamily } from "./model";
import { SECTION_ORDER } from "./model";

const credits = JSON.parse(readFileSync(resolve(dirname(fileURLToPath(import.meta.url)),
  "../../../app/about/credits.json"), "utf8")) as { sources: { id: string }[] };
const FAMILIES: LicenceFamily[] = ["cc0", "pdm", "nkc", "by", "by-sa", "by-nc", "by-nc-sa"];
const both: [string, AboutContent][] = [["en", aboutEn], ["es", aboutEs]];

const inlines = (b: Block): Inline[] => (b.kind === "p" ? b.text : b.kind === "list" ? b.items.flat()
  : b.kind === "figure" ? b.caption : []);
const links = (xs: Inline[]) => xs.flatMap((x) => (typeof x === "object" && "href" in x ? [x.href] : []));
const maths = (b: Block) => (b.kind === "math" ? [b.tex] : inlines(b).flatMap((x) => (typeof x === "object" && "m" in x
  ? [x.m] : [])));
const shape = (b: Block) => (b.kind === "figure" ? `figure:${b.figure}` : b.kind === "live" ? `live:${b.what}`
  : b.kind === "list" ? `list:${b.items.length}` : b.kind);

describe("the About content", () => {
  it("has every section, in order, in both languages", () => {
    for (const [, content] of both) expect(content.sections.map((s) => s.id)).toEqual(SECTION_ORDER);
  });

  it("says the same in both languages: blocks, equations, figures, links", () => {
    aboutEn.sections.forEach((en, i) => {
      const es = aboutEs.sections[i];
      expect(es.blocks.map(shape), en.id).toEqual(en.blocks.map(shape));
      expect(es.blocks.flatMap(maths), en.id).toEqual(en.blocks.flatMap(maths));
      expect(es.blocks.flatMap((b) => links(inlines(b))), en.id).toEqual(en.blocks.flatMap((b) => links(inlines(b))));
    });
    for (const key of Object.keys(aboutEn.figures) as (keyof AboutContent["figures"])[]) {
      expect(Object.keys(aboutEs.figures[key]).sort(), key).toEqual(Object.keys(aboutEn.figures[key]).sort());
    }
    expect(Object.keys(aboutEs.live).sort()).toEqual(Object.keys(aboutEn.live).sort());
  });

  it("describes every source and every licence family the policy accepts", () => {
    for (const [lang, content] of both) {
      for (const { id } of credits.sources) expect(content.sources, `${lang} ${id}`).toHaveProperty(id);
      expect(content.sources, lang).toHaveProperty("contribution");
      for (const family of FAMILIES) {
        expect(content.licences[family]?.name, `${lang} ${family}`).toBeTruthy();
        expect(content.licences[family]?.text.length, `${lang} ${family}`).toBeGreaterThan(0);
      }
    }
  });

  it("typesets every equation", () => {
    for (const [, content] of both) {
      for (const tex of content.sections.flatMap((s) => s.blocks.flatMap(maths))) {
        expect(() => katex.renderToString(tex, { throwOnError: true }), tex).not.toThrow();
      }
    }
  });

  it("uses no em dash and no arrow (ADR-0067)", () => {
    for (const [lang, content] of both) {
      const text = JSON.stringify(content);
      expect(text.includes("—"), lang).toBe(false);
      expect(text.includes("→"), lang).toBe(false);
    }
  });
});
