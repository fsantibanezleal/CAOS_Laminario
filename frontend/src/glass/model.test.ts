import { describe, expect, it } from "vitest";
import {
  ARRANGEMENTS, BOX_ROWS, FOLDER_PLACES, LIFT_MM, STANDARD, carouselRing, coverslipSide, folderPages, layout,
  stepFromKey,
} from "./model";

describe("the glass slide's anatomy", () => {
  it("keeps a 22 mm coverslip between the frosted ends of a standard slide", () => {
    expect(coverslipSide(STANDARD)).toBe(22);
    // A 46 x 27 mm thin section: the coverslip shrinks to the space between its ends.
    expect(coverslipSide({ long: 46, short: 27, label: 13.8 })).toBeCloseTo(46 - 27.6 - 3);
  });
});

describe("the carousel", () => {
  it("never lets neighbouring slides touch, whatever the set's size", () => {
    for (const n of [1, 2, 3, 7, 18, 40, 200]) {
      const { step, radius } = carouselRing(n);
      expect(2 * radius * Math.sin(step / 2)).toBeGreaterThanOrEqual(85.9);
    }
  });

  it("puts the chosen slide in front, facing the visitor, and hides the far side", () => {
    const placed = layout("carousel", 18, 5);
    expect(placed[5].position[0]).toBeCloseTo(0);
    expect(placed[5].position[2]).toBeCloseTo(0);
    expect(placed[5].rotation[1]).toBeCloseTo(0);
    expect(placed[4].position[0]).toBeLessThan(0);
    expect(placed[6].position[0]).toBeGreaterThan(0);
    expect(placed.filter((p) => !p.visible).length).toBeGreaterThan(0);
  });
});

describe("the drawer and the box", () => {
  it("stand the slides one behind the other, the chosen one lifted to show its label", () => {
    const placed = layout("drawer", 12, 3);
    const zs = placed.map((p) => p.position[2]);
    expect([...zs].sort((a, b) => b - a)).toEqual(zs);
    expect(placed[3].position[1]).toBe(LIFT_MM);
    expect(placed.filter((p) => p.position[1] > 0)).toHaveLength(1);
  });

  it("keep a box's slides in two rows side by side", () => {
    const xs = new Set(layout("box", 30, 0).map((p) => p.position[0]));
    expect(xs.size).toBe(BOX_ROWS);
  });
});

describe("the folder", () => {
  it("lays 20 slides flat in two columns of ten, one page at a time", () => {
    const placed = layout("folder", 45, 23);
    expect(placed.filter((p) => p.visible)).toHaveLength(FOLDER_PLACES);
    expect(placed[23].visible && placed[20].visible && !placed[19].visible).toBe(true);
    expect(folderPages(45)).toBe(3);
    expect(placed[20].rotation[0]).toBeCloseTo(-Math.PI / 2);
  });
});

describe("every arrangement", () => {
  it("places every slide of the set", () => {
    for (const a of ARRANGEMENTS) {
      for (const n of [1, 3, 25]) expect(layout(a, n, 0)).toHaveLength(n);
    }
  });

  it("moves through the set with the keyboard, within its ends", () => {
    expect(stepFromKey("ArrowRight", 2, 5)).toBe(3);
    expect(stepFromKey("ArrowRight", 4, 5)).toBe(4);
    expect(stepFromKey("ArrowLeft", 0, 5)).toBe(0);
    expect(stepFromKey("End", 0, 5)).toBe(4);
    expect(stepFromKey("PageDown", 0, 45)).toBe(20);
    expect(stepFromKey("a", 0, 5)).toBeNull();
  });
});
