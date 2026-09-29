import { describe, expect, it } from "vitest";
import { formatDate, pluralKey } from "./format";

describe("formatDate", () => {
  it("shows a calendar day as that day in every time zone", () => {
    // The first specimen label showed 30 August for a slide collected on 31 August 1962 (UTC-3).
    expect(formatDate("en", "1962-08-31")).toBe("August 31, 1962");
    expect(formatDate("es", "1962-08-31")).toBe("31 de agosto de 1962");
  });

  it("keeps an instant in the visitor's zone", () => {
    const instant = new Date(Date.UTC(2026, 8, 29, 12, 0, 0));
    expect(formatDate("en", instant, { timeZone: "UTC", dateStyle: "medium" })).toBe("Sep 29, 2026");
  });
});

describe("pluralKey", () => {
  const has = (keys: string[]) => (k: string) => keys.includes(k);
  it("picks the CLDR category, and other when the catalogue lacks it", () => {
    expect(pluralKey("en", "count.slides", 1, has(["count.slides.one", "count.slides.other"]))).toBe("count.slides.one");
    expect(pluralKey("en", "count.slides", 505, has(["count.slides.one", "count.slides.other"])))
      .toBe("count.slides.other");
    // Spanish has a "many" category for millions; a catalogue without it falls back to "other".
    expect(pluralKey("es", "count.slides", 1_000_000, has(["count.slides.one", "count.slides.other"])))
      .toBe("count.slides.other");
  });
});
