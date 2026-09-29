// What a photograph says about itself, read in the browser before anything is sent (R-087): the date it was taken,
// its orientation and its GPS position, by exifr. exifr reads JPEG, PNG, TIFF and HEIF; for WebP the EXIF chunk's
// TIFF block is handed to it. Only the start of a large file is read: a scanner file is never loaded whole.
import exifr from "exifr";
import { kindOf, stripLocation, type PhotoKind } from "./location";

export interface PhotoReading {
  kind: PhotoKind;
  taken: string | null;
  orientation: number | null;
  gps: { lat: number; lon: number } | null;
}

/** Files up to this size are read whole (a photograph); above it, only the first megabyte (a scanner file). */
export const READ_WHOLE_BYTES = 64 * 1024 * 1024;
const HEAD_BYTES = 1024 * 1024;

/** The WebP file's EXIF chunk (a TIFF block, sometimes after an "Exif\0\0" prefix), or null. */
export function webpExif(data: Uint8Array): Uint8Array | null {
  let at = 12;
  while (at + 8 <= data.length) {
    const fourcc = String.fromCharCode(...data.subarray(at, at + 4));
    const size = new DataView(data.buffer, data.byteOffset + at + 4, 4).getUint32(0, true);
    if (fourcc === "EXIF") {
      const body = data.subarray(at + 8, at + 8 + size);
      const prefixed = String.fromCharCode(...body.subarray(0, 6)) === "Exif\0\0";
      return prefixed ? body.subarray(6) : body;
    }
    at += 8 + size + (size & 1);
  }
  return null;
}

/** "2019:04:20 10:00:00" (EXIF, no zone) as the contract's ISO date-time "2019-04-20T10:00:00". */
export function isoDate(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const m = /^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})/.exec(value.trim());
  if (!m || m[1] === "0000") return null;
  return `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}`;
}

async function bytesOf(blob: Blob, whole: boolean): Promise<Uint8Array> {
  const part = whole ? blob : blob.slice(0, HEAD_BYTES);
  return new Uint8Array(await part.arrayBuffer());
}

/** Read a file's date, orientation and position; a file exifr cannot read gives nulls, never an error. */
export async function readPhoto(blob: Blob): Promise<PhotoReading> {
  const data = await bytesOf(blob, blob.size <= READ_WHOLE_BYTES);
  return readPhotoBytes(data);
}

export async function readPhotoBytes(data: Uint8Array): Promise<PhotoReading> {
  const kind = kindOf(data);
  const empty: PhotoReading = { kind, taken: null, orientation: null, gps: null };
  const source = kind === "webp" ? webpExif(data) : kind === "other" ? null : data;
  if (!source) return empty;
  try {
    const tags = await exifr.parse(source, {
      tiff: true, exif: true, gps: false, xmp: false, icc: false, iptc: false, jfif: false, ihdr: false,
      reviveValues: false, translateValues: false, translateKeys: true,
    }) as Record<string, unknown> | undefined;
    const gps = await exifr.gps(source).catch(() => undefined);
    const valid = gps && Number.isFinite(gps.latitude) && Number.isFinite(gps.longitude)
      && !(gps.latitude === 0 && gps.longitude === 0);
    return {
      kind,
      taken: isoDate(tags?.DateTimeOriginal) ?? isoDate(tags?.CreateDate) ?? isoDate(tags?.ModifyDate),
      orientation: typeof tags?.Orientation === "number" ? tags.Orientation : null,
      gps: valid ? { lat: gps.latitude, lon: gps.longitude } : null,
    };
  } catch {
    return empty;
  }
}

/**
 * The file without its location (a private case, R-1204): rewritten in the browser, the position and the XMP
 * packets gone, its name and type kept. Returns the file unchanged when there was nothing to remove.
 */
export async function withoutLocation(file: File): Promise<{ file: File; gps: number; xmp: number }> {
  const data = new Uint8Array(await file.arrayBuffer());
  const out = stripLocation(data);
  if (!out.gps && !out.xmp) return { file, gps: 0, xmp: 0 };
  const bytes = new Uint8Array(out.data.byteLength);
  bytes.set(out.data);
  return { file: new File([bytes.buffer], file.name, { type: file.type, lastModified: file.lastModified }),
    gps: out.gps, xmp: out.xmp };
}

/** Whether the browser can draw the file as a picture (for the thumbnail beside its fields). */
export function drawable(file: File): boolean {
  return /^image\/(jpeg|png|webp|gif|avif)$/.test(file.type);
}

/** The kinds of scanner file the server reads (app/imaging): named so the page can say what it received. */
export const SCANNER_EXTENSIONS = [".svs", ".ndpi", ".mrxs", ".scn", ".vms", ".vmu", ".bif", ".tif", ".tiff",
  ".dcm", ".zip", ".isyntax"] as const;

export function looksLikeScannerFile(name: string, size: number): boolean {
  const lower = name.toLowerCase();
  return SCANNER_EXTENSIONS.some((ext) => lower.endsWith(ext)) && (size > READ_WHOLE_BYTES || !/\.tiff?$/.test(lower));
}
