import { afterEach, beforeAll, describe, expect, it } from "vitest";
import { sheetUrl, testPageUrl } from "../people/api";
import { clampOffset, pagesFor, savedOffset, savedStock, saveOffset, saveStock } from "./printing";

// The tests run in Node, which has no Web Storage: a map stands in for the browser's.
beforeAll(() => {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => { store.set(k, String(v)); },
    removeItem: (k: string) => { store.delete(k); },
    clear: () => store.clear(),
  } });
});
afterEach(() => localStorage.clear());

describe("the printer offset", () => {
  it("is bounded to 10 mm either way, in 0.1 mm steps", () => {
    expect(clampOffset(0.04)).toBe(0);
    expect(clampOffset(-0.26)).toBe(-0.3);
    expect(clampOffset(12)).toBe(10);
    expect(clampOffset(-40)).toBe(-10);
    expect(clampOffset(Number.NaN)).toBe(0);
  });

  it("is kept per stock on the device", () => {
    saveOffset("a4-plain", { dx: 0.5, dy: -1.24 });
    expect(savedOffset("a4-plain")).toEqual({ dx: 0.5, dy: -1.2 });
    expect(savedOffset("divbio-misl-1000")).toEqual({ dx: 0, dy: 0 });
    localStorage.setItem("laminario.labels.offset.broken", "{not json");
    expect(savedOffset("broken")).toEqual({ dx: 0, dy: 0 });
  });

  it("remembers the stock only while it exists", () => {
    saveStock("labtag-cla-4wh");
    expect(savedStock(["a4-plain", "labtag-cla-4wh"], "a4-plain")).toBe("labtag-cla-4wh");
    expect(savedStock(["a4-plain"], "a4-plain")).toBe("a4-plain");
  });
});

describe("a sheet", () => {
  it("fills pages from its start position", () => {
    expect(pagesFor(0, 0, 72)).toBe(0);
    expect(pagesFor(72, 0, 72)).toBe(1);
    expect(pagesFor(2, 71, 72)).toBe(2);
    expect(pagesFor(500, 10, 66)).toBe(8);
  });

  it("names its slides, start, offset and language in its address", () => {
    const url = new URL(sheetUrl({ stock: "a4-plain", slides: ["ABCD2345", "WXYZ6789"], start: 5,
      offset: { dx: 0.5, dy: -0.26 }, lang: "es" }), "http://x");
    expect(url.pathname).toBe("/api/labels/sheet.pdf");
    expect(Object.fromEntries(url.searchParams)).toEqual({ stock: "a4-plain", slides: "ABCD2345,WXYZ6789", start: "5",
      dx: "0.5", dy: "-0.3", lang: "es" });
    const test = new URL(testPageUrl("divbio-misl-1000", { dx: 0, dy: 1 }), "http://x");
    expect(Object.fromEntries(test.searchParams)).toEqual({ stock: "divbio-misl-1000", test: "true", dx: "0.0",
      dy: "1.0" });
  });
});
