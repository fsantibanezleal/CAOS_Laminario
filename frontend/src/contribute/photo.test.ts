// R-087: a photograph's date, orientation and position are read before upload, in each accepted format, and a private
// case's file leaves without its position.
import exifr from "exifr";
import { describe, expect, it } from "vitest";
import { exifBlock, IMAGE, join, jpeg, png, webp } from "./fixtures";
import { isoDate, looksLikeScannerFile, readPhoto, readPhotoBytes, webpExif, withoutLocation } from "./photo";

const SANTIAGO = { lat: -(33 + 26 / 60 + 56 / 3600), lon: -(70 + 39 / 60) };

describe("reading a photograph", () => {
  for (const [kind, make] of [["jpeg", jpeg], ["png", png], ["webp", webp], ["tiff", () => join(exifBlock(), IMAGE)]] as const) {
    it(`reads the date, the orientation and the position of a ${kind}`, async () => {
      const read = await readPhotoBytes(make());
      expect(read.kind).toBe(kind);
      expect(read.gps?.lat).toBeCloseTo(SANTIAGO.lat, 4);
      expect(read.gps?.lon).toBeCloseTo(SANTIAGO.lon, 4);
      expect(read.orientation).toBe(6);
      expect(read.taken).toBe("2019-04-20T10:00:00");
    });
  }

  it("finds the WebP EXIF chunk with or without its Exif prefix", () => {
    const block = webpExif(webp())!;
    expect([block[0], block[1]]).toEqual([0x49, 0x49]);
  });

  it("writes EXIF dates as the contract's ISO date-times, and refuses empty ones", () => {
    expect(isoDate("2019:04:20 10:00:00")).toBe("2019-04-20T10:00:00");
    expect(isoDate("0000:00:00 00:00:00")).toBeNull();
    expect(isoDate(undefined)).toBeNull();
  });

  it("reads a file that is not a photograph as nothing, without an error", async () => {
    expect(await readPhotoBytes(new Uint8Array([1, 2, 3, 4]))).toEqual({ kind: "other", taken: null,
      orientation: null, gps: null });
  });

  it("reads from a File, and rewrites it without its position", async () => {
    const file = new File([jpeg().slice().buffer as ArrayBuffer], "place.jpg", { type: "image/jpeg" });
    expect((await readPhoto(file)).gps).not.toBeNull();
    const clean = await withoutLocation(file);
    expect([clean.gps, clean.xmp, clean.file.name, clean.file.type]).toEqual([1, 1, "place.jpg", "image/jpeg"]);
    const bytes = new Uint8Array(await clean.file.arrayBuffer());
    expect(await exifr.gps(bytes)).toBeUndefined();
    expect((await readPhoto(clean.file)).taken).toBe("2019-04-20T10:00:00");
    const again = await withoutLocation(clean.file);
    expect(again.file).toBe(clean.file);
  });

  it("tells a scanner file from a photograph by its name and size", () => {
    expect(looksLikeScannerFile("CMU-1.svs", 177_552_579)).toBe(true);
    expect(looksLikeScannerFile("slide.ndpi", 10)).toBe(true);
    expect(looksLikeScannerFile("field.tif", 3_000_000)).toBe(false);
    expect(looksLikeScannerFile("field.jpg", 3_000_000)).toBe(false);
  });
});
