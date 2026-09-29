// R-1503: a slide's citation, and each image's title, author, source, licence with its link, and adaptation.
import { describe, expect, it } from "vitest";
import { attribution, slideCitation, type CiteWords } from "./cite";

const WORDS: CiteWords = { kind: "Microscope slide", readOn: "Read on", by: "by", from: "from",
  unknownAuthor: "an unknown author", pyramid: "adapted: re-encoded as a tiled pyramid",
  fused: "adapted: fused from a focal stack", reencoded: "adapted: re-encoded" };
const RECORD = { id: "7K2QD4MN", permalink: "https://laminario.ml.fasl-work.com/s/7K2QD4MN",
  published_at: "2026-09-23T10:00:00", label: { name: "Polyplax borealis", catalogue_number: "NHMUK010173454",
    preparation: "whole_mount" } } as const;
const BY = { uri: "https://creativecommons.org/licenses/by/4.0/", short_name: "CC BY 4.0" };

describe("citing and crediting", () => {
  it("cites a slide as the NHM Data Portal cites a record", () => {
    expect(slideCitation(RECORD as never, "whole mount", "29 September 2026", WORDS)).toBe(
      "Laminario (2026). Polyplax borealis (NHMUK010173454), whole mount [Microscope slide]. "
      + "https://laminario.ml.fasl-work.com/s/7K2QD4MN. Read on 29 September 2026.");
    const plain = { ...RECORD, published_at: null, label: { ...RECORD.label, catalogue_number: null } };
    expect(slideCitation(plain as never, "whole mount", "today", WORDS)).toContain("(7K2QD4MN)");
  });

  it("credits an image by title, author, source and licence, and says it is adapted", () => {
    const scan = { role: "pyramid", family: "micro", caption: null, creator: null,
      rights_holder: "The Trustees of the Natural History Museum, London", licence: BY,
      source: { url: "https://data.nhm.ac.uk/media/58dd40f2", record_id: "NHMUK010173454", retrieved_on: "2026-09-23",
        sha256: "a".repeat(64) } };
    expect(attribution(scan as never, RECORD as never, "Whole-slide image", WORDS)).toBe(
      "\"Whole-slide image, Polyplax borealis (NHMUK010173454)\" by The Trustees of the Natural History Museum, "
      + "London, from https://data.nhm.ac.uk/media/58dd40f2, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); "
      + "adapted: re-encoded as a tiled pyramid.");
    const composite = { ...scan, role: "edf_wavelet", creator: "Hunt, Gene", caption: "Ostracod, all in focus" };
    expect(attribution(composite as never, RECORD as never, "All in focus", WORDS)).toBe(
      "\"Ostracod, all in focus\" by Hunt, Gene, from https://data.nhm.ac.uk/media/58dd40f2, CC BY 4.0 "
      + "(https://creativecommons.org/licenses/by/4.0/); adapted: fused from a focal stack.");
    // A contribution has no source record: the slide's own page is where it resides.
    const photo = { role: "slide_overview", family: "macro", caption: null, creator: "A. Contributor",
      rights_holder: null, licence: BY, source: null };
    expect(attribution(photo as never, RECORD as never, "The slide", WORDS)).toContain(
      "from https://laminario.ml.fasl-work.com/s/7K2QD4MN, CC BY 4.0");
    expect(attribution(photo as never, RECORD as never, "The slide", WORDS)).toMatch(/adapted: re-encoded\.$/);
    const anonymous = { ...photo, creator: null };
    expect(attribution(anonymous as never, RECORD as never, "The slide", WORDS)).toContain("by an unknown author");
  });
});
