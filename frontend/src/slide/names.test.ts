import { describe, expect, it } from "vitest";
import { breakPoints, geometry, nameParts, trayReference } from "./names";

const taxon = (name: string, rank: string) => ({ kind: "taxon" as const, rank, name });

describe("names", () => {
  it("sets the epithets italic and the authorship roman", () => {
    expect(nameParts(taxon("Austrogoniodes keleri Clay, 1967", "species"))).toEqual([
      { text: "Austrogoniodes", italic: true }, { text: "keleri", italic: true }, { text: "Clay, 1967", italic: false }]);
    expect(nameParts(taxon("Pinus sylvestris var. mongolica Litv.", "variety"))).toEqual([
      { text: "Pinus", italic: true }, { text: "sylvestris", italic: true }, { text: "var.", italic: false },
      { text: "mongolica", italic: true }, { text: "Litv.", italic: false }]);
    expect(nameParts(taxon("Polyplax (Linnaeus, 1758)", "genus"))).toEqual([
      { text: "Polyplax", italic: true }, { text: "(Linnaeus, 1758)", italic: false }]);
  });

  it("keeps names above genus, rocks and minerals roman", () => {
    expect(nameParts(taxon("Pediculidae", "family"))).toEqual([{ text: "Pediculidae", italic: false }]);
    expect(nameParts({ kind: "rock", rank: null, name: "Granite" })).toEqual([{ text: "Granite", italic: false }]);
  });

  it("lays every format long side across, with a label end in proportion", () => {
    expect(geometry({ width_mm: 76, height_mm: 26 })).toEqual({ long: 76, short: 26, label: 20 });
    expect(geometry({ width_mm: 27, height_mm: 46 })).toEqual({ long: 46, short: 27, label: 13.8 });
  });

  it("breaks a catalogue number between its letters and digits, never inside the digits", () => {
    expect(breakPoints("NHMUK010668672")).toEqual(["NHMUK", "010668672"]);
    expect(breakPoints("USNM 1234-A")).toEqual(["USNM ", "1234-", "A"]);
    expect(breakPoints("2SX4707K")).toEqual(["2", "SX", "4707", "K"]);
  });

  it("scales a tray to its longest slide, never below the 2 x 3 in format", () => {
    expect(trayReference([{ width_mm: 76, height_mm: 26 }, { width_mm: 46, height_mm: 27 }])).toBe(76.2);
    expect(trayReference([{ width_mm: 100, height_mm: 30 }])).toBe(100);
  });
});
