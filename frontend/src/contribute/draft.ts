// A slide case as the contribute place holds it while the contributor fills it in, and its conversion to the
// ingestion contract (SlideCaseSubmission) the server validates. Text fields hold strings as typed; the conversion
// trims them, drops the empty ones and reads the numbers, so the server's validation (R-1202) is the one that
// speaks, next to the field its path names. The unsent case is kept on this device (the files cannot be: a browser
// does not keep a chosen file across a reload, so an image then asks for its file again).
import type { AssetSpec, SlideCaseSubmission } from "../contract/ingest";
import type { Calibration } from "./calibration";

export type Family = AssetSpec["family"];
export type Role = AssetSpec["role"];
export type Modality = NonNullable<AssetSpec["modality"]>;
export type Slide = SlideCaseSubmission["slide"];
export type Specimen = SlideCaseSubmission["specimen"];
export type AnchorValue = Specimen["anchor"];

export const FORMATS = ["iso_76x26", "us_75x25", "petro_27x46", "us_2x3in", "custom"] as const;
export const COVERSLIPS = ["none", "18x18", "22x22", "22x40", "22x50", "24x50", "24x60", "custom"] as const;
export const PREPARATIONS = ["whole_mount", "section", "smear", "squash", "strew", "thin_section", "polished_section",
  "peel", "cast", "fluid_mount"] as const;
export const ANCHOR_KINDS = ["taxon", "rock", "mineral", "crystal", "material"] as const;
export const GEOPRIVACY = ["open", "obscured", "private"] as const;
export const PRESERVATION = ["recent", "fossil", "in_amber"] as const;
export const TYPE_STATUS = ["holotype", "paratype", "allotype", "syntype", "lectotype", "paralectotype", "neotype",
  "topotype", "other"] as const;
export const MODALITIES = ["brightfield", "darkfield", "phase_contrast", "dic", "polarised_ppl", "polarised_xpl",
  "reflected", "fluorescence", "sem_external"] as const;
export const ROLES_BY_FAMILY: Record<Family, readonly Role[]> = {
  macro: ["specimen", "place", "slide_overview", "label"],
  micro: ["single", "pyramid", "z_plane", "polarised"],
};

/** Slide sizes in mm (long, short), from app/contracts/vocab: drawn in the preview. */
export const SLIDE_MM: Record<Exclude<Slide["format"], "custom">, [number, number]> = {
  iso_76x26: [76, 26], us_75x25: [75, 25], petro_27x46: [46, 27], us_2x3in: [76.2, 50.8],
};
export const COVERSLIP_MM: Record<Exclude<NonNullable<Slide["coverslip"]>, "none" | "custom">, [number, number]> = {
  "18x18": [18, 18], "22x22": [22, 22], "22x40": [40, 22], "22x50": [50, 22], "24x50": [50, 24], "24x60": [60, 24],
};

/** Licences a contribution may carry (app/contracts/licences.py), the first the one offered first. */
export const LICENCES = [
  { uri: "https://creativecommons.org/licenses/by/4.0/", short: "CC BY 4.0" },
  { uri: "https://creativecommons.org/licenses/by-sa/4.0/", short: "CC BY-SA 4.0" },
  { uri: "https://creativecommons.org/licenses/by-nc/4.0/", short: "CC BY-NC 4.0" },
  { uri: "https://creativecommons.org/licenses/by-nc-sa/4.0/", short: "CC BY-NC-SA 4.0" },
  { uri: "https://creativecommons.org/publicdomain/zero/1.0/", short: "CC0 1.0" },
  // Earlier versions, for an image already published under one (the policy accepts 2.0 to 4.0 of BY and BY-SA).
  { uri: "https://creativecommons.org/licenses/by/3.0/", short: "CC BY 3.0" },
  { uri: "https://creativecommons.org/licenses/by-sa/3.0/", short: "CC BY-SA 3.0" },
] as const;

/** What the browser read from a photograph before anything was sent. */
export interface PhotoFacts {
  taken?: string | null;
  orientation?: number | null;
  gps?: { lat: number; lon: number } | null;
  /** A position was there when the case was last sent (a reopened case no longer has the file to read it from). */
  gpsPresent?: boolean;
  /** The file was rewritten without its position (a private case). */
  stripped?: boolean;
}

export interface ImageDraft {
  /** The image's own id in the case (``upload_id``), kept across changes so its file stays with it. */
  token: string;
  family: Family;
  role: Role;
  source: "file" | "iiif";
  remoteIiif: string;
  licence: string;
  creator: string;
  rightsHolder: string;
  pixelSize: string;
  calibration: Calibration | null;
  modality: Modality | "";
  planeIndex: string;
  planeDepth: string;
  planeStack: string;
  polarisation: "ppl" | "xpl";
  polarisationAngle: string;
  caption: string;
  photo: PhotoFacts | null;
  /** The file's name and size, kept with the case; the File itself only in memory. */
  fileName: string | null;
  fileSize: number | null;
}

export interface CaseDraft {
  slide: {
    format: Slide["format"];
    customW: string;
    customH: string;
    coverslip: NonNullable<Slide["coverslip"]>;
    coverW: string;
    coverH: string;
    preparation: Slide["preparation"] | "";
    stain: string;
    mountant: string;
    catalogueNumber: string;
    labelNote: string;
    preparedOn: string;
    preparer: string;
  };
  specimen: {
    /** The kind chosen before a name is (the name, once chosen, carries its own). */
    kindChoice: AnchorValue["kind"];
    anchor: AnchorValue | null;
    host: AnchorValue | null;
    part: string;
    preservation: NonNullable<Specimen["preservation"]>;
    typeStatus: NonNullable<Specimen["type_status"]> | "";
    collectedOn: string;
    collector: string;
    locality: string;
    lat: string;
    lon: string;
    uncertainty: string;
    country: string;
    geoprivacy: NonNullable<Specimen["geoprivacy"]>;
  };
  placement: { node: string; overrideReason: string };
  images: ImageDraft[];
}

/** A random image id: 16 characters of the alphabet the contract allows ([A-Za-z0-9_+-], 8 to 128). */
export function newToken(): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
}

export function emptyCase(): CaseDraft {
  return {
    slide: { format: "iso_76x26", customW: "", customH: "", coverslip: "none", coverW: "", coverH: "",
      preparation: "", stain: "", mountant: "", catalogueNumber: "", labelNote: "", preparedOn: "", preparer: "" },
    specimen: { kindChoice: "taxon", anchor: null, host: null, part: "", preservation: "recent", typeStatus: "", collectedOn: "",
      collector: "", locality: "", lat: "", lon: "", uncertainty: "", country: "", geoprivacy: "open" },
    placement: { node: "", overrideReason: "" },
    images: [],
  };
}

export function newImage(family: Family, creator = ""): ImageDraft {
  return {
    token: newToken(), family, role: family === "macro" ? "specimen" : "single", source: "file", remoteIiif: "",
    licence: LICENCES[0].uri, creator, rightsHolder: "", pixelSize: "", calibration: null,
    modality: family === "micro" ? "brightfield" : "", planeIndex: "", planeDepth: "", planeStack: "",
    polarisation: "ppl", polarisationAngle: "0", caption: "", photo: null, fileName: null, fileSize: null,
  };
}

const text = (value: string): string | null => (value.trim() ? value.trim() : null);

/**
 * A number as typed ("0,25" too, as Spanish writes it); null when empty. Text that is not a number is sent as it
 * is, so the server's validation names the field (a NaN would travel as null and hide the mistake).
 */
export function number(value: string): number | null {
  const v = value.trim().replace(",", ".");
  if (!v) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : (value.trim() as unknown as number);
}

/** A pair of sizes: null when both are empty (the rule then says a size is missing), else both as typed. */
function size(w: string, h: string): { w_mm: number; h_mm: number } | null {
  if (!w.trim() && !h.trim()) return null;
  return { w_mm: number(w) as number, h_mm: number(h) as number };
}

function asset(image: ImageDraft): AssetSpec {
  const spec: AssetSpec = {
    family: image.family, role: image.role, licence: image.licence,
    rights_holder: text(image.rightsHolder), creator: text(image.creator), caption: text(image.caption),
  };
  if (image.source === "iiif") spec.remote_iiif = text(image.remoteIiif);
  else spec.upload_id = image.token;
  if (image.family === "micro") {
    spec.pixel_size_um = number(image.pixelSize);
    spec.modality = image.modality || null;
    if (image.role === "z_plane") {
      spec.plane = { index: number(image.planeIndex) as number, depth_um: number(image.planeDepth) as number,
        stack: image.planeStack.trim() };
    }
    if (image.role === "polarised") {
      spec.polarisation = { state: image.polarisation, angle_deg: number(image.polarisationAngle) ?? 0 };
    }
  }
  if (image.photo) {
    spec.exif = { datetime_original: image.photo.taken ?? null,
      gps_present: Boolean(image.photo.gps || image.photo.gpsPresent) && !image.photo.stripped };
  }
  return spec;
}

/** The case as the contract has it. Fields left empty are left out; the server says what is missing. */
export function toSubmission(draft: CaseDraft): SlideCaseSubmission {
  const s = draft.slide;
  const p = draft.specimen;
  const lat = number(p.lat);
  const lon = number(p.lon);
  return {
    origin: "contribution",
    slide: {
      format: s.format,
      custom_mm: s.format === "custom" ? size(s.customW, s.customH) : null,
      coverslip: s.coverslip,
      coverslip_custom_mm: s.coverslip === "custom" ? size(s.coverW, s.coverH) : null,
      preparation: (s.preparation || undefined) as Slide["preparation"],
      stain: text(s.stain), mountant: text(s.mountant), catalogue_number: text(s.catalogueNumber),
      label_note: text(s.labelNote), prepared_on: text(s.preparedOn), preparer: text(s.preparer),
    },
    specimen: {
      // Left out until chosen, so the server says it is required (a null would read as the wrong type).
      anchor: (p.anchor ?? undefined) as AnchorValue,
      host: p.anchor?.kind === "taxon" ? p.host : null,
      part: p.anchor?.kind === "taxon" ? text(p.part) : null,
      preservation: p.anchor?.kind === "taxon" ? p.preservation : "recent",
      type_status: p.typeStatus || null,
      collected_on: text(p.collectedOn), collector: text(p.collector), locality_text: text(p.locality),
      coordinates: lat === null && lon === null ? null
        : { lat: lat as number, lon: lon as number, uncertainty_m: number(p.uncertainty) },
      country: text(p.country)?.toUpperCase() ?? null,
      geoprivacy: p.geoprivacy,
    },
    placement: { node: (draft.placement.node || undefined) as string,
      override_reason: text(draft.placement.overrideReason) },
    assets: draft.images.map(asset) as SlideCaseSubmission["assets"],
  };
}

/** The draft a stored case reopens as (GET /api/slide-cases/{id} gives the submission as last sent). */
export function fromSubmission(sub: SlideCaseSubmission): CaseDraft {
  const s = sub.slide;
  const p = sub.specimen;
  const str = (v: unknown) => (v === null || v === undefined ? "" : String(v));
  return {
    slide: { format: s.format, customW: str(s.custom_mm?.w_mm), customH: str(s.custom_mm?.h_mm),
      coverslip: s.coverslip ?? "none", coverW: str(s.coverslip_custom_mm?.w_mm), coverH: str(s.coverslip_custom_mm?.h_mm),
      preparation: s.preparation, stain: str(s.stain), mountant: str(s.mountant), catalogueNumber: str(s.catalogue_number),
      labelNote: str(s.label_note), preparedOn: str(s.prepared_on), preparer: str(s.preparer) },
    specimen: { kindChoice: p.anchor.kind, anchor: p.anchor, host: p.host ?? null, part: str(p.part), preservation: p.preservation ?? "recent",
      typeStatus: p.type_status ?? "", collectedOn: str(p.collected_on), collector: str(p.collector),
      locality: str(p.locality_text), lat: str(p.coordinates?.lat), lon: str(p.coordinates?.lon),
      uncertainty: str(p.coordinates?.uncertainty_m), country: str(p.country), geoprivacy: p.geoprivacy ?? "open" },
    placement: { node: sub.placement.node, overrideReason: str(sub.placement.override_reason) },
    images: sub.assets.map((a) => ({
      ...newImage(a.family),
      token: a.upload_id ?? newToken(), role: a.role, source: a.remote_iiif ? "iiif" : "file",
      remoteIiif: str(a.remote_iiif), licence: a.licence, creator: str(a.creator), rightsHolder: str(a.rights_holder),
      pixelSize: str(a.pixel_size_um), modality: a.modality ?? "", planeIndex: str(a.plane?.index),
      planeDepth: str(a.plane?.depth_um), planeStack: str(a.plane?.stack),
      polarisation: a.polarisation?.state ?? "ppl", polarisationAngle: str(a.polarisation?.angle_deg ?? 0),
      caption: str(a.caption),
      photo: a.exif ? { taken: a.exif.datetime_original ?? null, gps: null, gpsPresent: Boolean(a.exif.gps_present) }
        : null,
    })),
  };
}

// --- where the server's messages go ------------------------------------------------------------------------------

export type Section = "specimen" | "slide" | "images" | "place" | "placement";

/** The section of the form a contract path belongs to ("specimen.coordinates.lat" is the place section). */
export function sectionOf(path: string): Section {
  if (path.startsWith("slide")) return "slide";
  if (path.startsWith("assets")) return "images";
  if (path.startsWith("placement")) return "placement";
  if (/^specimen\.(coordinates|locality_text|country|geoprivacy)/.test(path)) return "place";
  return "specimen";
}

/** The image a path names ("assets.2.licence" is the third image), or null. */
export function imageOf(path: string): number | null {
  const m = /^assets\.(\d+)/.exec(path);
  return m ? Number(m[1]) : null;
}

/** Messages by field path, for the fields to show; a nested path also counts for its parents' field. */
export function byField<T extends { field: string }>(items: T[]): Map<string, T[]> {
  const map = new Map<string, T[]>();
  for (const item of items) {
    const list = map.get(item.field) ?? [];
    list.push(item);
    map.set(item.field, list);
  }
  return map;
}

// --- kept on this device -----------------------------------------------------------------------------------------

const STORE_KEY = "laminario.contribute.unsent";

export function saveUnsent(draft: CaseDraft): void {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(draft));
  } catch {
    // storage full or blocked: the case lasts for this page only
  }
}

export function loadUnsent(): CaseDraft | null {
  try {
    const text = localStorage.getItem(STORE_KEY);
    if (!text) return null;
    const draft = JSON.parse(text) as CaseDraft;
    return draft && draft.slide && draft.specimen && Array.isArray(draft.images) ? draft : null;
  } catch {
    return null;
  }
}

export function forgetUnsent(): void {
  try {
    localStorage.removeItem(STORE_KEY);
  } catch {
    // nothing to forget
  }
}
