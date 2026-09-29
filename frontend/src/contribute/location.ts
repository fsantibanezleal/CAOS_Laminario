// A photograph's location, removed in the browser before it is sent when the specimen's place is private (R-087,
// R-1204). The routine works on the file's bytes, never decoding the image: the GPS directory of every TIFF-structured
// EXIF block is emptied (its entry count set to 0, its entries and their out-of-line values zeroed, so no coordinate
// stays in the file), and every XMP packet (where a position can also be written) is removed, or zeroed inside a TIFF.
// The image data, the date and the orientation are kept. The server checks the result (R-1203).
//
//   JPEG  the APP1 "Exif" segment holds a TIFF block; XMP is another APP1 segment (and extended XMP)
//   PNG   the eXIf chunk holds a TIFF block (its CRC is computed again); XMP is an iTXt chunk
//   WebP  the EXIF chunk holds a TIFF block; XMP is the "XMP " chunk (the VP8X flag and the RIFF size follow)
//   TIFF  the file's own first directory points to the GPS directory; XMP is tag 700

export type PhotoKind = "jpeg" | "png" | "webp" | "tiff" | "other";

export interface Stripped {
  data: Uint8Array;
  kind: PhotoKind;
  /** GPS directories emptied, and XMP packets removed or zeroed. */
  gps: number;
  xmp: number;
}

const GPS_POINTER = 0x8825;
const XMP_TAG = 700;
const TYPE_SIZE: Record<number, number> = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8 };
const XMP_ID = "http://ns.adobe.com/xap/1.0/\0";
const XMP_EXTENSION_ID = "http://ns.adobe.com/xmp/extension/\0";

export function kindOf(data: Uint8Array): PhotoKind {
  if (data[0] === 0xff && data[1] === 0xd8) return "jpeg";
  if (data[0] === 0x89 && data[1] === 0x50 && data[2] === 0x4e && data[3] === 0x47) return "png";
  if (ascii(data, 0, 4) === "RIFF" && ascii(data, 8, 4) === "WEBP") return "webp";
  if ((data[0] === 0x49 && data[1] === 0x49 && data[2] === 0x2a) || (data[0] === 0x4d && data[1] === 0x4d && data[3] === 0x2a)) {
    return "tiff";
  }
  return "other";
}

function ascii(data: Uint8Array, at: number, length: number): string {
  return String.fromCharCode(...data.subarray(at, at + length));
}

/**
 * Empty the GPS directory of the TIFF structure that starts at ``base`` within ``data`` (edited in place), and zero
 * an XMP packet it holds (tag 700). Returns how many GPS directories and XMP packets were cleared.
 */
export function clearTiff(data: Uint8Array, base: number, end = data.length): { gps: number; xmp: number } {
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const little = data[base] === 0x49;
  if (view.getUint16(base + 2, little) !== 42) return { gps: 0, xmp: 0 }; // BigTIFF (43) is not a photograph's EXIF
  const u16 = (at: number) => view.getUint16(base + at, little);
  const u32 = (at: number) => view.getUint32(base + at, little);
  const inside = (at: number, length: number) => at >= 0 && base + at + length <= end;
  let gps = 0;
  let xmp = 0;
  const ifd0 = u32(4);
  if (!inside(ifd0, 2)) return { gps, xmp };
  const entries = u16(ifd0);
  for (let i = 0; i < entries; i += 1) {
    const entry = ifd0 + 2 + i * 12;
    if (!inside(entry, 12)) break;
    const tag = u16(entry);
    if (tag === GPS_POINTER) {
      const at = u32(entry + 8);
      if (inside(at, 2)) gps += emptyDirectory(data, view, base, at, little, end);
    } else if (tag === XMP_TAG) {
      const size = (TYPE_SIZE[u16(entry + 2)] ?? 1) * u32(entry + 4);
      const at = size > 4 ? u32(entry + 8) : entry + 8 - 0;
      if (size > 4 && inside(at, size)) {
        data.fill(0, base + at, base + at + size);
        xmp += 1;
      }
    }
  }
  return { gps, xmp };
}

function emptyDirectory(data: Uint8Array, view: DataView, base: number, at: number, little: boolean,
  end: number): number {
  const count = view.getUint16(base + at, little);
  for (let i = 0; i < count; i += 1) {
    const entry = base + at + 2 + i * 12;
    if (entry + 12 > end) break;
    const size = (TYPE_SIZE[view.getUint16(entry + 2, little)] ?? 1) * view.getUint32(entry + 4, little);
    if (size > 4) {
      const value = base + view.getUint32(entry + 8, little);
      if (value + size <= end) data.fill(0, value, value + size);
    }
  }
  data.fill(0, base + at + 2, Math.min(base + at + 2 + count * 12, end));
  view.setUint16(base + at, 0, little);
  return count > 0 ? 1 : 0;
}

function stripJpeg(input: Uint8Array): Stripped {
  const parts: Uint8Array[] = [input.subarray(0, 2)];
  let gps = 0;
  let xmp = 0;
  let at = 2;
  while (at + 4 <= input.length && input[at] === 0xff) {
    const marker = input[at + 1];
    if (marker === 0xda || marker === 0xd9) break; // the image data (or its end): copied unchanged below
    const length = (input[at + 2] << 8) | input[at + 3];
    const segment = input.slice(at, at + 2 + length);
    if (marker === 0xe1) {
      const id = ascii(segment, 4, XMP_EXTENSION_ID.length);
      if (ascii(segment, 4, 6) === "Exif\0\0") {
        const cleared = clearTiff(segment, 10);
        gps += cleared.gps;
        xmp += cleared.xmp;
      } else if (id.startsWith(XMP_ID) || id === XMP_EXTENSION_ID) {
        xmp += 1;
        at += 2 + length;
        continue;
      }
    }
    parts.push(segment);
    at += 2 + length;
  }
  parts.push(input.subarray(at));
  return { data: concat(parts), kind: "jpeg", gps, xmp };
}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

export function crc32(bytes: Uint8Array): number {
  let c = 0xffffffff;
  for (const b of bytes) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function stripPng(input: Uint8Array): Stripped {
  const parts: Uint8Array[] = [input.subarray(0, 8)];
  let gps = 0;
  let xmp = 0;
  let at = 8;
  while (at + 12 <= input.length) {
    const view = new DataView(input.buffer, input.byteOffset + at, 8);
    const length = view.getUint32(0);
    const type = ascii(input, at + 4, 4);
    const chunk = input.slice(at, at + 12 + length);
    if (type === "eXIf") {
      const cleared = clearTiff(chunk, 8, 8 + length);
      gps += cleared.gps;
      xmp += cleared.xmp;
      new DataView(chunk.buffer).setUint32(8 + length, crc32(chunk.subarray(4, 8 + length)));
    } else if ((type === "iTXt" || type === "tEXt" || type === "zTXt") && ascii(chunk, 8, 17) === "XML:com.adobe.xmp") {
      xmp += 1;
      at += 12 + length;
      continue;
    }
    parts.push(chunk);
    at += 12 + length;
    if (type === "IEND") break;
  }
  return { data: concat(parts), kind: "png", gps, xmp };
}

function stripWebp(input: Uint8Array): Stripped {
  const chunks: Uint8Array[] = [];
  let gps = 0;
  let xmp = 0;
  let at = 12;
  while (at + 8 <= input.length) {
    const size = new DataView(input.buffer, input.byteOffset + at + 4, 4).getUint32(0, true);
    const padded = size + (size & 1);
    const fourcc = ascii(input, at, 4);
    const chunk = input.slice(at, at + 8 + padded);
    if (fourcc === "EXIF") {
      const start = ascii(chunk, 8, 6) === "Exif\0\0" ? 14 : 8;
      const cleared = clearTiff(chunk, start, 8 + size);
      gps += cleared.gps;
      xmp += cleared.xmp;
    } else if (fourcc === "XMP ") {
      xmp += 1;
      at += 8 + padded;
      continue;
    }
    chunks.push(chunk);
    at += 8 + padded;
  }
  for (const chunk of chunks) {
    if (ascii(chunk, 0, 4) === "VP8X" && xmp) chunk[8] &= ~0x04; // the XMP-present flag
  }
  const body = concat(chunks);
  const header = input.slice(0, 12);
  new DataView(header.buffer).setUint32(4, 4 + body.length, true);
  return { data: concat([header, body]), kind: "webp", gps, xmp };
}

function stripTiff(input: Uint8Array): Stripped {
  const data = input.slice();
  const cleared = clearTiff(data, 0);
  return { data, kind: "tiff", ...cleared };
}

/** The file with its location removed; a file of another kind is returned unchanged. */
export function stripLocation(input: Uint8Array): Stripped {
  const kind = kindOf(input);
  if (kind === "jpeg") return stripJpeg(input);
  if (kind === "png") return stripPng(input);
  if (kind === "webp") return stripWebp(input);
  if (kind === "tiff") return stripTiff(input);
  return { data: input, kind, gps: 0, xmp: 0 };
}

function concat(parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) {
    out.set(p, at);
    at += p.length;
  }
  return out;
}
