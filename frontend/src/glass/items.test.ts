import { describe, expect, it } from "vitest";
import type { CollectionNodeRecord, SlideSummary } from "../contract/catalog";
import type { TreeIndex } from "../tree/TreeProvider";
import { hueToken, nodeItem, slideItem } from "./items";
import { STANDARD } from "./model";

const i18n = {
  lang: "en",
  t: (key: string) => (key === "cabinet.empty" ? "empty" : key),
  plural: (key: string, n: number) => `${n} ${key.split(".")[1]}`,
  date: (d: string) => d,
} as never;

const node = (over: Partial<CollectionNodeRecord> = {}): CollectionNodeRecord => ({
  id: "life.plants.green-algae", level: "sub-collection", name: { en: "Green algae", es: "Algas verdes" },
  about: { en: "", es: "" }, icon: "life.plants.green-algae", slide_count: 4, ...over,
});

const tree = {
  realms: [], byId: new Map([["life.plants.green-algae", node()]]), parentOf: new Map(),
  facets: new Map([["preparation", { id: "preparation", values: [{ id: "whole_mount", name: { en: "Whole mount", es: "Montaje entero" } }] }]]),
  countries: { CO: { en: "Colombia", es: "Colombia" } },
} as unknown as TreeIndex;

const summary = (over: Partial<SlideSummary> = {}): SlideSummary => ({
  id: "V4VPG60M", permalink: "https://laminario.ml.fasl-work.com/s/V4VPG60M",
  anchor: { kind: "taxon", ref: "1", name: "Chlorella vulgaris Beij.", rank: "species" } as never,
  format: { width_mm: 76, height_mm: 26 } as never, placement: { node: "life.plants.green-algae" } as never,
  preparation: "whole_mount", thumbnail_url: "/iiif/x/full/!320,320/0/default.jpg", origin: "base",
  label: { catalogue_number: "USNM 1", locality_text: "Boyacá, Colombia", country: "CO", collected_on: "2024-05-15" },
  ...over,
});

describe("a node as a glass slide", () => {
  it("carries the node's icon, name, counts and the collection's hue", () => {
    const item = nodeItem(node({ children: [node(), node()] }), i18n);
    expect(item.icon).toBe("life.plants.green-algae");
    expect(item.name).toBe("Green algae");
    expect(item.facts).toEqual(["4 slides", "2 drawers"]);
    expect(item.format).toEqual(STANDARD);
    expect(item.href).toBe("/c/plants/green-algae");
    expect(item.empty).toBe(false);
    expect(hueToken("life.plants.green-algae")).toBe("--h-plants");
    expect(hueToken("life")).toBe("--c-accent");
  });

  it("says when a drawer is empty and draws it fainter", () => {
    const item = nodeItem(node({ slide_count: 0 }), i18n);
    expect(item.empty).toBe(true);
    expect(item.facts).toContain("empty");
  });
});

describe("a slide as a glass slide", () => {
  it("shows the specimen's image under the coverslip, its name in italic when a species, and its facts", () => {
    const item = slideItem(summary(), tree, i18n);
    expect(item.image).toContain("/iiif/");
    expect(item.photo).toBeNull();
    expect(item.italic).toBe(true);
    expect(item.reference).toBe("USNM 1");
    // The country is not repeated when the locality ends with it.
    expect(item.facts).toEqual(["Whole mount", "Boyacá, Colombia", "2024-05-15"]);
    expect(item.format).toEqual({ long: 76, short: 26, label: 20 });
    expect(item.href).toBe("/s/V4VPG60M");
  });

  it("is its own photograph when the glass was photographed", () => {
    const item = slideItem(summary({ glass_photo_url: "/media/V4VPG60M/899-abc.jpg" }), tree, i18n);
    expect(item.photo).toBe("/media/V4VPG60M/899-abc.jpg");
  });

  it("keeps a thin section's own proportion", () => {
    const item = slideItem(summary({ format: { width_mm: 46, height_mm: 27 } as never }), tree, i18n);
    expect(item.format.long).toBe(46);
    expect(item.format.short).toBe(27);
    expect(item.format.label).toBeLessThan(20);
  });
});
