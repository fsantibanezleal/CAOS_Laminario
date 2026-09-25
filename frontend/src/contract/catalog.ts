// Generated from contracts/catalog.schema.json by frontend/scripts/generate-contract-types.mjs. Do not edit by hand;
// run `npm run contract:generate` after scripts/export_contracts.py. A drift fails the build.
export interface LaminarioCatalog {
  slide?: SlideRecord;
  slidePage?: SlidePage;
  slideSummary?: SlideSummary;
  validation?: ValidationResult;
}
export interface SlideRecord {
  id: string;
  permalink: string;
  qr_payload: string;
  status: "draft" | "processing" | "published" | "hidden";
  origin: "base" | "contribution";
  format: FormatRecord;
  coverslip?: CoverslipRecord | null;
  label: LabelRecord;
  anchor: AnchorRecord;
  host?: AnchorRecord | null;
  place: PlaceRecord;
  placement: PlacementRecord;
  quality: QualityRecord;
  assets: AssetRecord[];
  manifest_url: string;
  created_at: string;
  updated_at: string;
  published_at?: string | null;
}
export interface FormatRecord {
  code: string;
  width_mm: number;
  height_mm: number;
}
export interface CoverslipRecord {
  code: string;
  long_mm: number;
  short_mm: number;
}
/**
 * What the printed label shows.
 */
export interface LabelRecord {
  name: string;
  catalogue_number?: string | null;
  preparation: string;
  stain?: string | null;
  mountant?: string | null;
  label_note?: string | null;
  prepared_on?: string | null;
  preparer?: string | null;
  collected_on?: string | null;
  collector?: string | null;
  locality_text?: string | null;
  type_status?: string | null;
}
export interface AnchorRecord {
  kind: "taxon" | "rock" | "mineral" | "crystal" | "material";
  ref: string;
  name: string;
  rank?: string | null;
}
/**
 * Where the specimen was collected, after geoprivacy.
 */
export interface PlaceRecord {
  geoprivacy: "open" | "obscured" | "private";
  point?: PointRecord | null;
  cell?: CellRecord | null;
  uncertainty_m?: number | null;
  locality_text?: string | null;
}
export interface PointRecord {
  lat: number;
  lon: number;
}
export interface CellRecord {
  south: number;
  west: number;
  north: number;
  east: number;
}
export interface PlacementRecord {
  node: string;
  overridden?: boolean;
}
export interface QualityRecord {
  badge: "verified" | "needs_id" | "reference";
  checks: QualityCheckRecord[];
}
export interface QualityCheckRecord {
  code: "licence_and_provenance" | "scale" | "modality" | "macro_and_micro";
  passed: boolean;
  detail: string;
}
export interface AssetRecord {
  id: number;
  family: "macro" | "micro";
  role: string;
  sort_order: number;
  status: "pending" | "ready" | "failed";
  media: MediaRecord;
  pixel_size_um?: number | null;
  modality?: string | null;
  plane?: PlaneRecord | null;
  polarisation?: PolarisationRecord | null;
  caption?: string | null;
  licence: LicenceRecord;
  rights_holder?: string | null;
  creator?: string | null;
  source?: SourceRecord | null;
}
export interface MediaRecord {
  kind: "pyramid" | "image" | "remote_iiif";
  iiif_info_url?: string | null;
  image_url?: string | null;
  width_px?: number | null;
  height_px?: number | null;
}
export interface PlaneRecord {
  stack: string;
  index: number;
  depth_um: number;
}
export interface PolarisationRecord {
  state: "ppl" | "xpl";
  angle_deg: number;
}
export interface LicenceRecord {
  uri: string;
  short_name: string;
}
export interface SourceRecord {
  url: string;
  record_id: string;
  retrieved_on: string;
  sha256: string;
}
export interface SlidePage {
  items: SlideSummary[];
  total: number;
  offset: number;
  limit: number;
}
/**
 * A slide in a list: enough to draw it in a drawer.
 */
export interface SlideSummary {
  id: string;
  permalink: string;
  anchor: AnchorRecord;
  format: FormatRecord;
  placement: PlacementRecord;
  preparation: string;
  thumbnail_url?: string | null;
  origin: "base" | "contribution";
}
/**
 * The answer of ``POST /api/slide-cases/validate``.
 */
export interface ValidationResult {
  valid: boolean;
  flags?: ValidationFlag[];
  errors?: ValidationError[];
}
export interface ValidationFlag {
  code: string;
  field: string;
  message: string;
}
export interface ValidationError {
  field: string;
  message: string;
  expected: string;
}
