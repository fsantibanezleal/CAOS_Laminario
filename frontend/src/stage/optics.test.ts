import { describe, expect, it } from "vitest";
import { objectiveAt, scaleBar, turret } from "./optics";

describe("the turret (R-1104)", () => {
  it("offers the steps that do not magnify beyond the image, and labels finer ones as digital zoom", () => {
    // The NMNH ostracod: 0.229 um per pixel, scanned at 40x.
    const steps = turret(0.229);
    expect(steps.map((s) => s.objective)).toEqual([2, 4, 10, 20, 40, 100]);
    expect(steps.filter((s) => !s.digital).map((s) => s.objective)).toEqual([2, 4, 10, 20, 40]);
    expect(steps.find((s) => s.objective === 100)?.digital).toBe(true);
    // At 40x one screen pixel covers 0.25 um, and the image is shown at 0.916 screen pixels per image pixel.
    const forty = steps.find((s) => s.objective === 40)!;
    expect(forty.umPerScreenPixel).toBeCloseTo(0.25, 12);
    expect(forty.zoom).toBeCloseTo(0.916, 12);
    expect(objectiveAt(0.229, forty.zoom)).toBeCloseTo(40, 9);
  });

  it("offers nothing for an image without a pixel size", () => {
    expect(turret(null)).toEqual([]);
    expect(turret(0)).toEqual([]);
  });

  it("marks CMU-1's own 20x step as optical and 40x as digital", () => {
    const steps = turret(0.499);
    expect(steps.find((s) => s.objective === 20)?.digital).toBe(false);
    expect(steps.find((s) => s.objective === 40)?.digital).toBe(true);
  });
});

describe("the scale bar (R-086)", () => {
  it("is the longest 1-2-5 length within a quarter of the width, drawn at its true length", () => {
    const bar = scaleBar(0.25, 1200)!; // 40x: a quarter of 1200 px covers 75 um
    expect(bar.um).toBe(50);
    expect(bar.px).toBeCloseTo(200, 9);
    expect([bar.value, bar.unit]).toEqual([50, "µm"]);
  });

  it("changes unit at a millimetre", () => {
    const bar = scaleBar(5, 1200)!; // 2x: 300 px cover 1.5 mm
    expect([bar.um, bar.value, bar.unit]).toEqual([1000, 1, "mm"]);
    expect(bar.px).toBeCloseTo(200, 9);
  });

  it("stays within 1 percent of the physical distance at every step of a turret", () => {
    for (const pixel of [0.229, 0.499, 1.3]) {
      for (const step of turret(pixel)) {
        const bar = scaleBar(step.umPerScreenPixel, 1000)!;
        expect(Math.abs(bar.px * step.umPerScreenPixel - bar.um) / bar.um).toBeLessThan(0.01);
        expect(bar.px).toBeLessThanOrEqual(250);
      }
    }
  });

  it("draws nothing without a scale", () => {
    expect(scaleBar(0, 1000)).toBeNull();
    expect(scaleBar(Number.NaN, 1000)).toBeNull();
  });
});
