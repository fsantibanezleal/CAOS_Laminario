// R-1204: the location routine removes the GPS position and every XMP packet from JPEG, PNG, WebP and TIFF files and
// keeps their image data, date and orientation. The files are built here byte by byte, and read back with exifr, an
// independent reader, which is also what the contribute page uses to show the position.
import exifr from "exifr";
import { describe, expect, it } from "vitest";
import { exifBlock, IMAGE, join, jpeg, png, webp } from "./fixtures";
import { crc32, stripLocation } from "./location";

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
