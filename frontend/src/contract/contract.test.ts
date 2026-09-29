import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import type { CollectionTreeRecord, PlacementResult, SlideRecord, ValidationResult } from "./catalog";
import type { SlideCaseSubmission } from "./ingest";

// The generated types are the only contract the web knows; this test pins the shape a component relies on,
// so a schema change that renames or removes one of these fields fails here before it fails on a page.
describe("catalog contract", () => {
  it("exposes the slide record fields the interface renders", () => {
    const record: SlideRecord = {
      id: "7K3QX9M2",
      permalink: "https://laminario.example.org/s/7K3QX9M2",
      qr_payload: "HTTPS://LAMINARIO.EXAMPLE.ORG/S/7K3QX9M2",
      status: "published",
      origin: "base",
      format: { code: "iso_76x26", width_mm: 76, height_mm: 26 },
      label: { name: "Polyplax borealis", preparation: "whole_mount" },
      anchor: { kind: "taxon", ref: "1032608", name: "Polyplax borealis" },
      place: { geoprivacy: "open" },
      placement: { node: "life.insects.lice" },
      quality: { badge: "needs_id", checks: [] },
      assets: [],
      manifest_url: "https://laminario.example.org/api/slides/7K3QX9M2/manifest",
      created_at: "2026-09-25T00:00:00",
      updated_at: "2026-09-25T00:00:00",
    };
    expect(record.format.width_mm).toBe(76);
  });

  it("types a validation answer and a submission", () => {
    const answer: ValidationResult = { valid: false, errors: [{ field: "slide.format", message: "", expected: "" }] };
    const submission: SlideCaseSubmission = {
      slide: { format: "iso_76x26", preparation: "smear" },
      specimen: { anchor: { kind: "rock", ref: "basalt", name: "Basalt" } },
      placement: { node: "earth.rocks.igneous" },
      assets: [{ family: "micro", role: "single", licence: "https://creativecommons.org/licenses/by/4.0/" }],
    };
    expect(answer.valid).toBe(false);
    expect(submission.assets.length).toBe(1);
  });

  it("ships the schemas the types were generated from", () => {
    const schema = JSON.parse(readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), "../../../contracts/catalog.schema.json"), "utf8"));
    expect(Object.keys(schema.properties)).toEqual([
      "slide", "slidePage", "slideSummary", "validation", "job", "jobEvent", "account", "invitation",
      "createdSlideCase", "upload", "collectionTree", "collectionNode", "facet", "anchorSuggestion", "placement",
    ]);
  });

  it("types the collection tree and a placement answer", () => {
    const tree: CollectionTreeRecord = {
      realms: [{
        id: "life", level: "realm", name: { en: "Life", es: "Vida" }, about: { en: "", es: "" }, icon: "life",
        children: [{ id: "life.birds", level: "collection", name: { en: "Birds", es: "Aves" },
                     about: { en: "", es: "" }, icon: "life.birds", slide_count: 3 }],
      }],
      counts: { realm: 3, collection: 18, "sub-collection and group": 130 },
    };
    const placed: PlacementResult = {
      suggestion: "life.insects.lice",
      path: [{ id: "life", name: { en: "Life", es: "Vida" }, icon: "life" }],
      accepting: ["life", "life.insects", "life.insects.lice"],
    };
    expect(tree.realms[0].children?.[0].icon).toBe("life.birds");
    expect(placed.accepting).toContain(placed.suggestion);
  });
});
