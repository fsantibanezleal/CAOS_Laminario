// Generated from contracts/catalog.schema.json by frontend/scripts/generate-contract-types.mjs. Do not edit by hand;
// run `npm run contract:generate` after scripts/export_contracts.py. A drift fails the build.
export interface LaminarioCatalog {
  slide?: SlideRecord;
  slidePage?: SlidePage;
  slideSummary?: SlideSummary;
  validation?: ValidationResult;
  job?: JobRecord;
  jobEvent?: JobEventRecord;
  account?: AccountRecord;
  invitation?: InvitationRecord;
  createdSlideCase?: CreatedSlideCase;
  upload?: UploadRecord;
  collectionTree?: CollectionTreeRecord;
  collectionNode?: CollectionNodeDetail;
  facet?: FacetRecord;
  anchorSuggestion?: AnchorSuggestion;
  placement?: PlacementResult;
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
  part?: string | null;
  preservation?: "recent" | "fossil" | "in_amber";
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
  classification?: string | null;
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
  iiif_version?: (2 | 3) | null;
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
/**
 * A processing job as ``GET /api/jobs/{id}`` returns it.
 */
export interface JobRecord {
  id: string;
  kind: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  attempts: number;
  error?: string | null;
  result?: {
    [k: string]: unknown;
  } | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  events_url: string;
}
/**
 * One Server-Sent Event of a job's stream: its ``id`` field is ``seq``, its ``event`` field ``event``.
 */
export interface JobEventRecord {
  seq: number;
  event: "queued" | "started" | "progress" | "log" | "requeued" | "succeeded" | "failed" | "cancelled";
  data: {
    [k: string]: unknown;
  };
  at: string;
}
/**
 * An account as ``GET /api/users/me`` returns it.
 */
export interface AccountRecord {
  id: string;
  email: string;
  display_name: string;
  role: "contributor" | "identifier" | "curator" | "admin";
  is_active: boolean;
  is_verified: boolean;
}
/**
 * An invitation as its issuer sees it. ``link`` is present only in the answer that created it, and only
 * when it was not mailed: the token is never stored, so it cannot be shown again.
 */
export interface InvitationRecord {
  id: number;
  email?: string | null;
  role: "contributor" | "identifier" | "curator" | "admin";
  note?: string | null;
  status: "pending" | "used" | "expired" | "revoked";
  created_at: string;
  expires_at: string;
  mailed: boolean;
  link?: string | null;
}
/**
 * The answer of ``POST /api/slide-cases``: the new draft and the flags of its submission.
 */
export interface CreatedSlideCase {
  id: string;
  status: string;
  flags?: ValidationFlag[];
}
/**
 * An upload as its contributor sees it (``GET /api/uploads``).
 */
export interface UploadRecord {
  id: number;
  slide_id: string;
  asset_id: number;
  filename?: string | null;
  size: number;
  wsi: boolean;
  status: "uploading" | "received" | "accepted" | "rejected" | "cancelled";
  sniffed?: string | null;
  sha256?: string | null;
  reason?: string | null;
  job_id?: string | null;
  created_at: string;
  finished_at?: string | null;
}
/**
 * The whole tree: the three realms and everything under them.
 */
export interface CollectionTreeRecord {
  realms: CollectionNodeRecord[];
  counts: {
    [k: string]: number;
  };
}
/**
 * A node of the collection tree (``GET /api/collections``), with its published slides counted.
 */
export interface CollectionNodeRecord {
  id: string;
  level: "realm" | "collection" | "sub-collection" | "group";
  name: LocalisedText;
  about: LocalisedText;
  icon: string;
  view?: boolean;
  priority?: number;
  defined_by?: DefinitionRecord[];
  slide_count?: number;
  children?: CollectionNodeRecord[];
}
export interface LocalisedText {
  en: string;
  es: string;
}
/**
 * One condition of a node's rule, for people: a taxon with its GBIF page, a rock family, a part.
 */
export interface DefinitionRecord {
  kind:
    | "taxon"
    | "excluded-taxon"
    | "kind"
    | "rock"
    | "mineral"
    | "crystal"
    | "material"
    | "part"
    | "preservation"
    | "relation";
  value: string;
  label: string;
  url?: string | null;
}
/**
 * One node (``GET /api/collections/{id}``): itself with its children, and the path down to it.
 */
export interface CollectionNodeDetail {
  node: CollectionNodeRecord;
  path: NodeRef[];
  iiif_collection_url: string;
}
export interface NodeRef {
  id: string;
  name: LocalisedText;
  icon: string;
}
/**
 * A property that cuts across the tree, with the icon of each value.
 */
export interface FacetRecord {
  id: "preparation" | "modality" | "plant-organ" | "crystal-system";
  name: LocalisedText;
  values: FacetValueRecord[];
}
export interface FacetValueRecord {
  id: string;
  name: LocalisedText;
  icon: string;
}
/**
 * A name the anchor field can offer (``GET /api/anchors/search``).
 */
export interface AnchorSuggestion {
  ref: string;
  name: string;
  rank?: string | null;
  classification?: string | null;
  context?: string | null;
}
/**
 * Where a slide belongs (``POST /api/placement``): the suggestion, and every node that accepts it.
 */
export interface PlacementResult {
  anchor?: AnchorRecord | null;
  suggestion?: string | null;
  path?: NodeRef[];
  accepting?: string[];
  errors?: ValidationError[];
}
