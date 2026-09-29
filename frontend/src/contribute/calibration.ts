// A micro photograph's pixel size, calibrated on a photograph of a stage micrometer taken with the same camera and
// objective (R-1207). The contributor clicks both ends of a known length d on the micrometer; the two points are n
// pixels apart, so
//
//   p = d / n  (micrometres per pixel)
//
// Each click is uncertain by one pixel, so n is uncertain by two, and
//
//   dp = d * 2 / n^2 = 2p / n  (the relative uncertainty is 2 / n)
//
// which makes a calibration over too short a length visibly poor. The calibration photograph is not uploaded.

export interface Point {
  x: number;
  y: number;
}

export interface Calibration {
  /** Micrometres per pixel. */
  pixelSize: number;
  /** Its uncertainty, one pixel at each end, in micrometres per pixel. */
  uncertainty: number;
  /** The distance between the two points, in pixels. */
  pixels: number;
  /** The known length, in micrometres. */
  length: number;
}

/** The pixel sizes the contract accepts (app/contracts/ingest.py, AssetSpec.pixel_size_um). */
export const PIXEL_SIZE_RANGE = { min: 0.05, max: 50 } as const;

/** Units a stage micrometer's length is read in, and their size in micrometres. */
export const LENGTH_UNITS = { um: 1, mm: 1000 } as const;
export type LengthUnit = keyof typeof LENGTH_UNITS;

/**
 * The pixel size from two points a known length apart; null when the points are less than two pixels apart (the
 * uncertainty would equal the value) or the length is not positive.
 */
export function calibrate(a: Point, b: Point, length: number, unit: LengthUnit = "um"): Calibration | null {
  const pixels = Math.hypot(b.x - a.x, b.y - a.y);
  const um = length * LENGTH_UNITS[unit];
  if (!Number.isFinite(pixels) || !Number.isFinite(um) || pixels < 2 || um <= 0) return null;
  const pixelSize = um / pixels;
  return { pixelSize, uncertainty: (2 * pixelSize) / pixels, pixels, length: um };
}

/** Whether the contract accepts the value (the flow says so before the form sends it). */
export function withinRange(pixelSize: number): boolean {
  return pixelSize >= PIXEL_SIZE_RANGE.min && pixelSize <= PIXEL_SIZE_RANGE.max;
}

/**
 * The value and its uncertainty as written: the uncertainty to two significant figures, the value to the same
 * decimal place (the GUM's usual rule, section 7.2.6).
 */
export function written(c: Calibration): { value: string; uncertainty: string; decimals: number } {
  const exponent = Math.floor(Math.log10(c.uncertainty));
  const decimals = Math.max(0, 1 - exponent);
  return { value: c.pixelSize.toFixed(decimals), uncertainty: c.uncertainty.toFixed(decimals), decimals };
}

/** The value to store: the pixel size rounded to where its uncertainty makes further digits meaningless. */
export function stored(c: Calibration): number {
  return Number(written(c).value);
}
