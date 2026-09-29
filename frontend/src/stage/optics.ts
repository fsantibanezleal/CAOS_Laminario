// The stage's optics (R-1104, R-086). Scanner files pair an objective with a pixel size whose product is close to
// 10 um (CMU-1: 20x at 0.499 um; the NMNH ostracod: 40x at 0.229 um), so at objective M one screen pixel (a CSS
// pixel) covers 10 / M um. For an image whose pixel covers p um, objective M shows it at
//
//   zoom = p * M / 10 screen pixels per image pixel.
//
// A step whose zoom exceeds 1 shows the screen finer than the image: it is digital zoom and says so. The scale bar is
// the longest length of the 1-2-5 series that fits a quarter of the viewer's width, drawn at its true length for the
// current zoom.

export const OBJECTIVES = [2, 4, 10, 20, 40, 100] as const;
const MICRONS_PER_SCREEN_PIXEL_AT_1X = 10;

export interface Step {
  objective: number;
  /** Screen pixels per image pixel at this step. */
  zoom: number;
  /** Microns one screen pixel covers. */
  umPerScreenPixel: number;
  digital: boolean;
}

/** The turret for an image whose pixel covers ``pixelUm`` microns; none when the image has no pixel size. */
export function turret(pixelUm: number | null | undefined): Step[] {
  if (!pixelUm || pixelUm <= 0) return [];
  return OBJECTIVES.map((objective) => {
    const umPerScreenPixel = MICRONS_PER_SCREEN_PIXEL_AT_1X / objective;
    const zoom = pixelUm / umPerScreenPixel;
    return { objective, zoom, umPerScreenPixel, digital: zoom > 1 + 1e-9 };
  });
}

/** The objective a zoom corresponds to (screen pixels per image pixel), for the readout. */
export function objectiveAt(pixelUm: number, zoom: number): number {
  return (zoom * MICRONS_PER_SCREEN_PIXEL_AT_1X) / pixelUm;
}

export interface ScaleBar {
  /** The length the bar stands for, in microns. */
  um: number;
  /** Its drawn length, in screen pixels. */
  px: number;
  /** The length as text: "200 um" or "1 mm". */
  value: number;
  unit: "µm" | "mm";
}

const SERIES = [1, 2, 5];

/** The scale bar for ``umPerScreenPixel`` in a viewer ``width`` pixels wide, or null when nothing fits. */
export function scaleBar(umPerScreenPixel: number, width: number): ScaleBar | null {
  if (!(umPerScreenPixel > 0) || !(width > 0)) return null;
  const room = width / 4;
  let best: number | null = null;
  for (let exponent = -3; exponent <= 7; exponent += 1) {
    for (const lead of SERIES) {
      const um = lead * 10 ** exponent;
      if (um / umPerScreenPixel <= room) best = um;
    }
  }
  if (best === null) return null;
  // Round away binary noise from the powers of ten (0.1 * 3 and the like).
  const um = Number(best.toPrecision(6));
  return um >= 1000
    ? { um, px: um / umPerScreenPixel, value: Number((um / 1000).toPrecision(6)), unit: "mm" }
    : { um, px: um / umPerScreenPixel, value: um, unit: "µm" };
}
