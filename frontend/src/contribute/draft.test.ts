// The contribute place's case and the contract: what the form holds becomes the submission the server validates, and
// a stored case reopens as the same form.
import { describe, expect, it } from "vitest";
import { emptyCase, fromSubmission, imageOf, newImage, newToken, number, sectionOf, toSubmission,
  type CaseDraft } from "./draft";

function filled(): CaseDraft {
  const draft = emptyCase();
  draft.slide = { ...draft.slide, preparation: "whole_mount", stain: " Giemsa ", catalogueNumber: "LAM-0001",
    preparedOn: "2019-04" };
  draft.specimen = { ...draft.specimen, anchor: { kind: "taxon", ref: "4406063", name: "Pediculus humanus" },
    part: "", collectedOn: "2019-04-20", collector: "F. Santibañez", lat: "-33,4489", lon: "-70.6693",
    uncertainty: "30", country: "cl", geoprivacy: "obscured" };
  draft.placement.node = "life.insects.lice";
  const photo = newImage("macro", "F. Santibañez");
  photo.photo = { taken: "2019-04-20T10:00:00", gps: { lat: -33.4489, lon: -70.6693 } };
  const micro = newImage("micro", "F. Santibañez");
  micro.pixelSize = "0,25";
  micro.role = "z_plane";
  micro.planeIndex = "3";
  micro.planeDepth = "-1.5";
  micro.planeStack = "main";
  draft.images = [photo, micro];
  return draft;
}

describe("the case and the contract", () => {
  it("trims text, drops what is empty and reads numbers as Spanish writes them", () => {
    const sub = toSubmission(filled());
    expect(sub.slide.stain).toBe("Giemsa");
    expect(sub.slide.mountant).toBeNull();
    expect(sub.slide.custom_mm).toBeNull();
    expect(sub.specimen.coordinates).toEqual({ lat: -33.4489, lon: -70.6693, uncertainty_m: 30 });
    expect(sub.specimen.country).toBe("CL");
    expect(sub.specimen.part).toBeNull();
    expect(sub.assets[1]).toMatchObject({ family: "micro", role: "z_plane", pixel_size_um: 0.25, modality: "brightfield",
      plane: { index: 3, depth_um: -1.5, stack: "main" } });
    expect(sub.assets[0].exif).toEqual({ datetime_original: "2019-04-20T10:00:00", gps_present: true });
    expect(sub.assets[0].upload_id).toMatch(/^[A-Za-z0-9_+-]{8,128}$/);
  });

  it("sends a mistyped number as typed, so the server names the field", () => {
    expect(number("abc")).toBe("abc");
    expect(number(" ")).toBeNull();
    const draft = filled();
    draft.specimen.lat = "south";
    expect(toSubmission(draft).specimen.coordinates?.lat).toBe("south");
  });

  it("leaves out what does not apply: a host, a part and a preservation are an organism's", () => {
    const draft = filled();
    draft.specimen.anchor = { kind: "rock", ref: "granite", name: "Granite" };
    draft.specimen.host = { kind: "taxon", ref: "2436436", name: "Homo sapiens" };
    draft.specimen.part = "blood";
    draft.specimen.preservation = "fossil";
    const sub = toSubmission(draft);
    expect([sub.specimen.host, sub.specimen.part, sub.specimen.preservation]).toEqual([null, null, "recent"]);
  });

  it("a stripped photograph no longer carries a position", () => {
    const draft = filled();
    draft.images[0].photo = { ...draft.images[0].photo, stripped: true };
    expect(toSubmission(draft).assets[0].exif?.gps_present).toBe(false);
  });

  it("reopens a stored case as the same form, each image with its id", () => {
    const draft = filled();
    const again = fromSubmission(toSubmission(draft));
    expect(toSubmission(again)).toEqual(toSubmission(draft));
    expect(again.images.map((i) => i.token)).toEqual(draft.images.map((i) => i.token));
  });

  it("places each message in its section and image", () => {
    expect(sectionOf("slide.coverslip_custom_mm")).toBe("slide");
    expect(sectionOf("specimen.coordinates.lat")).toBe("place");
    expect(sectionOf("specimen.anchor.ref")).toBe("specimen");
    expect(sectionOf("assets.1.licence")).toBe("images");
    expect(sectionOf("placement.node")).toBe("placement");
    expect(imageOf("assets.12.plane.depth_um")).toBe(12);
    expect(imageOf("specimen.part")).toBeNull();
  });

  it("makes image ids of the contract's alphabet", () => {
    const ids = new Set(Array.from({ length: 200 }, newToken));
    expect(ids.size).toBe(200);
    for (const id of ids) expect(id).toMatch(/^[A-Za-z0-9]{16}$/);
  });
});
