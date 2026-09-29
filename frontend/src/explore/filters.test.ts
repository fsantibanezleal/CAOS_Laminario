import { describe, expect, it } from "vitest";
import { PAGE, apiQuery, readFilters, sortOf, toggle, writeFilters } from "./filters";

describe("filters in the address", () => {
  it("reads what it writes, with repeated facets and the pages shown", () => {
    const f = readFilters(new URLSearchParams("q=piojos&preparation=smear&preparation=section&country=GP&n=100"));
    expect(f.values.preparation).toEqual(["smear", "section"]);
    expect(f.shown).toBe(3 * PAGE); // 100 asked: the three pages that hold them
    expect(readFilters(writeFilters(f))).toEqual(f);
  });

  it("leaves out what is empty, so an unfiltered place has a bare address", () => {
    expect(writeFilters(readFilters(new URLSearchParams("q=&n=48&sort=bogus"))).toString()).toBe("");
  });

  it("sorts by relevance only while there are words", () => {
    expect(sortOf(readFilters(new URLSearchParams("q=lice")))).toBe("relevance");
    expect(sortOf(readFilters(new URLSearchParams("sort=relevance")))).toBe("newest");
    expect(sortOf(readFilters(new URLSearchParams("q=lice&sort=name")))).toBe("name");
  });

  it("asks the API for one whole-slide value, and for none when both are chosen", () => {
    let f = readFilters(new URLSearchParams("wsi=yes"));
    expect(apiQuery(f, {}, "life.insects").toString()).toBe("node=life.insects&wsi=true");
    f = toggle(f, "wsi", "no", true);
    expect(apiQuery(f).has("wsi")).toBe(false);
  });

  it("starts from the first page when a filter changes", () => {
    const f = readFilters(new URLSearchParams("n=144"));
    expect(toggle(f, "origin", "base", true).shown).toBe(PAGE);
  });
});
