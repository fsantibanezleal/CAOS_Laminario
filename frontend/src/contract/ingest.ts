// Generated from contracts/ingest.schema.json by frontend/scripts/generate-contract-types.mjs. Do not edit by hand;
// run `npm run contract:generate` after scripts/export_contracts.py. A drift fails the build.
export interface SlideCaseSubmission {
  origin?: "contribution" | "base";
  slide: SlideSpec;
  specimen: SpecimenSpec;
  placement: PlacementSpec;
  /**
   * @minItems 1
   * @maxItems 500
   */
  assets: [AssetSpec, ...AssetSpec[]];
}
export interface SlideSpec {
  format: "iso_76x26" | "us_75x25" | "petro_27x46" | "us_2x3in" | "custom";
  custom_mm?: SizeMm | null;
  coverslip?: "none" | "18x18" | "22x22" | "22x40" | "22x50" | "24x50" | "24x60" | "custom";
  coverslip_custom_mm?: CoverslipSizeMm | null;
  preparation:
    | "whole_mount"
    | "section"
    | "smear"
    | "squash"
    | "strew"
    | "thin_section"
    | "polished_section"
    | "peel"
    | "cast"
    | "fluid_mount";
  stain?: string | null;
  mountant?: string | null;
  catalogue_number?: string | null;
  label_note?: string | null;
  prepared_on?: string | null;
  preparer?: string | null;
}
/**
 * A custom slide size.
 */
export interface SizeMm {
  w_mm: number;
  h_mm: number;
}
/**
 * A custom coverslip size.
 */
export interface CoverslipSizeMm {
  w_mm: number;
  h_mm: number;
}
export interface SpecimenSpec {
  anchor: Anchor;
  collected_on?: string | null;
  collector?: string | null;
  locality_text?: string | null;
  coordinates?: Coordinates | null;
  geoprivacy?: "open" | "obscured" | "private";
  host?: Anchor | null;
  type_status?:
    | (
        | "holotype"
        | "paratype"
        | "allotype"
        | "syntype"
        | "lectotype"
        | "paralectotype"
        | "neotype"
        | "topotype"
        | "other"
      )
    | null;
}
/**
 * What the slide shows: a taxon, a rock, a mineral, a crystal or a material.
 */
export interface Anchor {
  kind: "taxon" | "rock" | "mineral" | "crystal" | "material";
  ref: string;
  name: string;
  rank?: string | null;
}
export interface Coordinates {
  lat: number;
  lon: number;
  uncertainty_m?: number | null;
}
export interface PlacementSpec {
  node: string;
  override_reason?: string | null;
}
export interface AssetSpec {
  family: "macro" | "micro";
  role: "slide_overview" | "specimen" | "place" | "label" | "single" | "pyramid" | "z_plane" | "polarised";
  upload_id?: string | null;
  remote_iiif?: string | null;
  source?: SourceSpec | null;
  licence: string;
  rights_holder?: string | null;
  creator?: string | null;
  pixel_size_um?: number | null;
  modality?:
    | (
        | "brightfield"
        | "darkfield"
        | "phase_contrast"
        | "dic"
        | "polarised_ppl"
        | "polarised_xpl"
        | "reflected"
        | "fluorescence"
        | "sem_external"
      )
    | null;
  plane?: PlaneSpec | null;
  polarisation?: PolarisationSpec | null;
  exif?: ExifSpec | null;
  caption?: string | null;
}
/**
 * Where an imported asset came from (the base collection).
 */
export interface SourceSpec {
  url: string;
  record_id: string;
  retrieved_on: string;
  sha256: string;
}
export interface PlaneSpec {
  index: number;
  depth_um: number;
  stack: string;
}
export interface PolarisationSpec {
  state: "ppl" | "xpl";
  angle_deg?: number;
}
/**
 * What the browser read from a photo's EXIF block, sent so the server can flag and strip.
 */
export interface ExifSpec {
  datetime_original?: string | null;
  gps_present?: boolean;
}
