// R-1204: the location routine removes the GPS position and every XMP packet from JPEG, PNG, WebP and TIFF files and
// keeps their image data, date and orientation. The files are built here byte by byte, and read back with exifr, an
// independent reader, which is also what the contribute page uses to show the position.
import exifr from "exifr";
import { describe, expect, it } from "vitest";
import { crc32, stripLocation } from "./location";

const enc = new TextEncoder();
const XMP = `<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description xmlns:exif="http://ns.adobe.com/exif/1.0/" exif:GPSLatitude="33,26.93S"/></rdf:RDF></x:xmpmeta>`;

/** A little-endian TIFF block: IFD0 with the orientation, the date and a pointer to a GPS IFD at Santiago. */
function exifBlock(): Uint8Array {
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

const IMAGE = Uint8Array.from({ length: 300 }, (_, i) => (i * 37) % 251);

function u16be(n: number) { return [n >> 8, n & 0xff]; }
function u32be(n: number) { return [(n >>> 24) & 0xff, (n >>> 16) & 0xff, (n >>> 8) & 0xff, n & 0xff]; }
function u32le(n: number) { return [n & 0xff, (n >>> 8) & 0xff, (n >>> 16) & 0xff, (n >>> 24) & 0xff]; }
function join(...parts: (Uint8Array | number[])[]) {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.length; }
  return out;
}

function jpeg(): Uint8Array {
  const exif = join(enc.encode("Exif\0\0"), exifBlock());
  const xmp = join(enc.encode("http://ns.adobe.com/xap/1.0/\0"), enc.encode(XMP));
  return join([0xff, 0xd8], [0xff, 0xe1], u16be(exif.length + 2), exif, [0xff, 0xe1], u16be(xmp.length + 2), xmp,
    [0xff, 0xda], u16be(8), [1, 2, 3, 4, 5, 6], IMAGE, [0xff, 0xd9]);
}

function pngChunk(type: string, data: Uint8Array) {
  const typed = join(enc.encode(type), data);
  return join(u32be(data.length), typed, u32be(crc32(typed)));
}

function png(): Uint8Array {
  const ihdr = new Uint8Array([0, 0, 0, 16, 0, 0, 0, 16, 8, 2, 0, 0, 0]);
  return join([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a], pngChunk("IHDR", ihdr), pngChunk("eXIf", exifBlock()),
    pngChunk("iTXt", join(enc.encode("XML:com.adobe.xmp\0\0\0\0\0"), enc.encode(XMP))), pngChunk("IDAT", IMAGE),
    pngChunk("IEND", new Uint8Array()));
}

function riffChunk(fourcc: string, data: Uint8Array) {
  return join(enc.encode(fourcc), u32le(data.length), data, data.length % 2 ? [0] : []);
}

function webp(): Uint8Array {
  const vp8x = new Uint8Array(10);
  vp8x[0] = 0x08 | 0x04; // EXIF and XMP present
  const body = join(riffChunk("VP8X", vp8x), riffChunk("VP8 ", IMAGE), riffChunk("EXIF", exifBlock()),
    riffChunk("XMP ", enc.encode(XMP)));
  return join(enc.encode("RIFF"), u32le(4 + body.length), enc.encode("WEBP"), body);
}

const has = (data: Uint8Array, text: string) => new TextDecoder("latin1").decode(data).includes(text);

describe("the location routine", () => {
  it("empties a JPEG's GPS directory and drops its XMP, keeping the image, date and orientation", async () => {
    const input = jpeg();
    expect((await exifr.gps(input))?.latitude).toBeCloseTo(-33.449, 3);
    const out = stripLocation(input);
    expect([out.kind, out.gps, out.xmp]).toEqual(["jpeg", 1, 1]);
    expect(await exifr.gps(out.data)).toBeUndefined();
    const kept = await exifr.parse(out.data, { gps: true, xmp: true });
    expect(kept.Orientation).toBeDefined();
    expect(kept.ModifyDate ?? kept.DateTime).toBeDefined();
    expect(has(out.data, "GPSLatitude") || has(out.data, "ns.adobe.com/xap")).toBe(false);
    const sos = input.indexOf(0xda, 4) - 1;
    expect(out.data.slice(out.data.length - (input.length - sos))).toEqual(input.slice(sos));
  });

  it("does the same for PNG, recomputing the chunk's CRC", async () => {
    const out = stripLocation(png());
    expect([out.kind, out.gps, out.xmp]).toEqual(["png", 1, 1]);
    expect(has(out.data, "XML:com.adobe.xmp")).toBe(false);
    // Every chunk's CRC is right.
    let at = 8;
    while (at < out.data.length) {
      const length = new DataView(out.data.buffer).getUint32(at);
      const stored = new DataView(out.data.buffer).getUint32(at + 8 + length);
      expect(stored).toBe(crc32(out.data.subarray(at + 4, at + 8 + length)));
      at += 12 + length;
    }
    expect(has(out.data, new TextDecoder("latin1").decode(IMAGE))).toBe(true);
  });

  it("does the same for WebP, clearing the XMP flag and fixing the RIFF size", () => {
    const out = stripLocation(webp());
    expect([out.kind, out.gps, out.xmp]).toEqual(["webp", 1, 1]);
    expect(has(out.data, "XMP ")).toBe(false);
    const view = new DataView(out.data.buffer);
    expect(view.getUint32(4, true)).toBe(out.data.length - 8);
    expect(out.data[20] & 0x04).toBe(0);
    expect(out.data[20] & 0x08).toBe(0x08);
  });

  it("empties a TIFF's own GPS directory", async () => {
    const tiff = join(exifBlock(), IMAGE);
    expect((await exifr.gps(tiff))?.longitude).toBeCloseTo(-70.65, 2);
    const out = stripLocation(tiff);
    expect([out.kind, out.gps]).toEqual(["tiff", 1]);
    expect(await exifr.gps(out.data)).toBeUndefined();
    // No coordinate stays in the bytes: the rationals of the latitude are gone.
    expect(new DataView(out.data.buffer).getUint32(300, true)).toBe(0);
  });

  it("leaves a file without a location, or of another kind, as it was", () => {
    const plain = new Uint8Array([0x47, 0x49, 0x46, 0x38, 0x39, 0x61]);
    expect(stripLocation(plain)).toEqual({ data: plain, kind: "other", gps: 0, xmp: 0 });
    const once = stripLocation(jpeg()).data;
    const twice = stripLocation(once);
    expect([twice.gps, twice.xmp]).toEqual([0, 0]);
    expect(twice.data).toEqual(once);
  });
});
