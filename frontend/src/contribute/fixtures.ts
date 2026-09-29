// Photographs built byte by byte for the tests of the location routine and the photo reader: a TIFF block with an
// orientation, a date and a GPS directory at Santiago, wrapped as JPEG, PNG and WebP, each with an XMP packet.
import { crc32 } from "./location";

export const enc = new TextEncoder();
export const XMP = `<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description xmlns:exif="http://ns.adobe.com/exif/1.0/" exif:GPSLatitude="33,26.93S"/></rdf:RDF></x:xmpmeta>`;

/** A little-endian TIFF block: IFD0 with the orientation, the date and a pointer to a GPS IFD at Santiago. */
export function exifBlock(): Uint8Array {
  const date = enc.encode("2019:04:20 10:00:00\0");
  const b = new Uint8Array(512);
  const v = new DataView(b.buffer);
  b.set([0x49, 0x49]);
  v.setUint16(2, 42, true);
  v.setUint32(4, 8, true);
  // IFD0 at 8: three entries.
  v.setUint16(8, 3, true);
  const entry = (at: number, tag: number, type: number, count: number, value: number) => {
    v.setUint16(at, tag, true); v.setUint16(at + 2, type, true); v.setUint32(at + 4, count, true);
    v.setUint32(at + 8, value, true);
  };
  entry(10, 0x0112, 3, 1, 6); // Orientation: 6 (rotated 90 degrees)
  entry(22, 0x0132, 2, date.length, 200); // DateTime, at 200
  entry(34, 0x8825, 4, 1, 100); // GPS IFD, at 100
  v.setUint32(46, 0, true);
  b.set(date, 200);
  // GPS IFD at 100: latitude ref, latitude (3 rationals at 300), longitude ref, longitude (at 330).
  v.setUint16(100, 4, true);
  entry(102, 1, 2, 2, 0x53); // "S"
  entry(114, 2, 5, 3, 300);
  entry(126, 3, 2, 2, 0x57); // "W"
  entry(138, 4, 5, 3, 330);
  v.setUint32(150, 0, true);
  const rationals = (at: number, values: number[]) => values.forEach((n, i) => {
    v.setUint32(at + i * 8, n, true); v.setUint32(at + i * 8 + 4, 1, true);
  });
  rationals(300, [33, 26, 56]);
  rationals(330, [70, 39, 0]);
  return b.subarray(0, 360);
}

export const IMAGE = Uint8Array.from({ length: 300 }, (_, i) => (i * 37) % 251);

function u16be(n: number) { return [n >> 8, n & 0xff]; }
function u32be(n: number) { return [(n >>> 24) & 0xff, (n >>> 16) & 0xff, (n >>> 8) & 0xff, n & 0xff]; }
function u32le(n: number) { return [n & 0xff, (n >>> 8) & 0xff, (n >>> 16) & 0xff, (n >>> 24) & 0xff]; }
export function join(...parts: (Uint8Array | number[])[]) {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.length; }
  return out;
}

export function jpeg(): Uint8Array {
  const exif = join(enc.encode("Exif\0\0"), exifBlock());
  const xmp = join(enc.encode("http://ns.adobe.com/xap/1.0/\0"), enc.encode(XMP));
  return join([0xff, 0xd8], [0xff, 0xe1], u16be(exif.length + 2), exif, [0xff, 0xe1], u16be(xmp.length + 2), xmp,
    [0xff, 0xda], u16be(8), [1, 2, 3, 4, 5, 6], IMAGE, [0xff, 0xd9]);
}

function pngChunk(type: string, data: Uint8Array) {
  const typed = join(enc.encode(type), data);
  return join(u32be(data.length), typed, u32be(crc32(typed)));
}

export function png(): Uint8Array {
  const ihdr = new Uint8Array([0, 0, 0, 16, 0, 0, 0, 16, 8, 2, 0, 0, 0]);
  return join([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a], pngChunk("IHDR", ihdr), pngChunk("eXIf", exifBlock()),
    pngChunk("iTXt", join(enc.encode("XML:com.adobe.xmp\0\0\0\0\0"), enc.encode(XMP))), pngChunk("IDAT", IMAGE),
    pngChunk("IEND", new Uint8Array()));
}

function riffChunk(fourcc: string, data: Uint8Array) {
  return join(enc.encode(fourcc), u32le(data.length), data, data.length % 2 ? [0] : []);
}

export function webp(): Uint8Array {
  const vp8x = new Uint8Array(10);
  vp8x[0] = 0x08 | 0x04; // EXIF and XMP present
  const body = join(riffChunk("VP8X", vp8x), riffChunk("VP8 ", IMAGE), riffChunk("EXIF", exifBlock()),
    riffChunk("XMP ", enc.encode(XMP)));
  return join(enc.encode("RIFF"), u32le(4 + body.length), enc.encode("WEBP"), body);
}
