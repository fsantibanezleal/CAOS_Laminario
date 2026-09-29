// R-1207: two points a known length apart give the length over their distance in pixels, with the uncertainty of
// one pixel at each end.
import { describe, expect, it } from "vitest";
import { calibrate, stored, withinRange, written } from "./calibration";

describe("calibration from a stage micrometer", () => {
  it("gives d / n and 2p / n", () => {
    // 100 um across 400 pixels, measured along a diagonal (240, 320): 0.25 um per pixel.
    const c = calibrate({ x: 10, y: 20 }, { x: 250, y: 340 }, 100)!;
    expect(c.pixels).toBeCloseTo(400, 10);
    expect(c.pixelSize).toBeCloseTo(0.25, 12);
    expect(c.uncertainty).toBeCloseTo(0.00125, 12);
    expect(c.uncertainty / c.pixelSize).toBeCloseTo(2 / 400, 12);
  });

  it("reads millimetres, the scale a stage micrometer is ruled in", () => {
    const c = calibrate({ x: 0, y: 0 }, { x: 2000, y: 0 }, 1, "mm")!;
    expect(c.length).toBe(1000);
    expect(c.pixelSize).toBeCloseTo(0.5, 12);
  });

  it("makes a short calibration visibly poor", () => {
    const long = calibrate({ x: 0, y: 0 }, { x: 1000, y: 0 }, 250)!;
    const short = calibrate({ x: 0, y: 0 }, { x: 20, y: 0 }, 5)!;
    expect(short.pixelSize).toBeCloseTo(long.pixelSize, 12);
    expect(short.uncertainty / long.uncertainty).toBeCloseTo(50, 9);
  });

  it("refuses points closer than two pixels, and a length that is not positive", () => {
    expect(calibrate({ x: 5, y: 5 }, { x: 6, y: 6 }, 10)).toBeNull();
    expect(calibrate({ x: 0, y: 0 }, { x: 100, y: 0 }, 0)).toBeNull();
    expect(calibrate({ x: 0, y: 0 }, { x: 100, y: 0 }, Number.NaN)).toBeNull();
  });

  it("writes the uncertainty to two significant figures and the value to the same place", () => {
    const c = calibrate({ x: 0, y: 0 }, { x: 400, y: 0 }, 100)!; // 0.25 +/- 0.00125
    expect(written(c)).toEqual({ value: "0.2500", uncertainty: "0.0013", decimals: 4 });
    expect(stored(c)).toBe(0.25);
    const coarse = calibrate({ x: 0, y: 0 }, { x: 30, y: 0 }, 100)!; // 3.333 +/- 0.222
    expect(written(coarse)).toEqual({ value: "3.33", uncertainty: "0.22", decimals: 2 });
  });

  it("checks the range the contract accepts", () => {
    expect(withinRange(0.25)).toBe(true);
    expect(withinRange(0.01)).toBe(false);
    expect(withinRange(80)).toBe(false);
  });
});
