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
  partRecord?: PartRecord;
  placement?: PlacementResult;
  facetCounts?: FacetCounts;
  map?: MapRecord;
  annotation?: AnnotationRecord;
  case?: CaseRecord;
  caseSummary?: CaseSummary;
  identifications?: IdentificationList;
  flag?: FlagRecord;
  moderationAction?: ModerationActionRecord;
  profile?: ProfileRecord;
  personIdentification?: PersonIdentificationRecord;
  stock?: StockRecord;
  about?: AboutRecord;
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
  contributor?: PersonRef | null;
  created_at: string;
  updated_at: string;
  published_at?: string | null;
}
export interface FormatRecord {
  code: string;
  width_mm: number;
  height_mm: number;
  assumed?: boolean;
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
  country?: string | null;
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
  community_node?: string | null;
  community_rank?: string | null;
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
  original_sha256?: string | null;
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
/**
 * An account as others may see it: its handle and display name, never its email (U14).
 */
export interface PersonRef {
  handle: string;
  name: string;
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
  glass_photo_url?: string | null;
  origin: "base" | "contribution";
  label?: SummaryLabel;
}
/**
 * What a drawer shows on a slide's label end (no coordinates, so nothing geoprivacy withholds).
 */
export interface SummaryLabel {
  catalogue_number?: string | null;
  collected_on?: string | null;
  locality_text?: string | null;
  country?: string | null;
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
  params?: {
    [k: string]: string;
  };
}
/**
 * A reason a slide case is refused: the field, the API's message and what would be accepted, and a stable code
 * with the values the message names, so an interface can say it in its own words (R-1202).
 */
export interface ValidationError {
  field: string;
  message: string;
  expected: string;
  code?: string | null;
  params?: {
    [k: string]: string;
  };
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
  handle?: string | null;
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
 * A part of an organism the part field offers (``GET /api/vocab/parts``), with its organ system.
 */
export interface PartRecord {
  id: string;
  group: string;
  name: LocalisedText;
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
/**
 * For each facet, its values under the current filters and how many slides each would match (the facet's own
 * filter left out, so a second value shows what it adds).
 */
export interface FacetCounts {
  collection?: {
    [k: string]: number;
  };
  kind?: {
    [k: string]: number;
  };
  preparation?: {
    [k: string]: number;
  };
  modality?: {
    [k: string]: number;
  };
  preservation?: {
    [k: string]: number;
  };
  country?: {
    [k: string]: number;
  };
  licence?: {
    [k: string]: number;
  };
  wsi?: {
    [k: string]: number;
  };
  origin?: {
    [k: string]: number;
  };
}
export interface MapRecord {
  countries: {
    [k: string]: number;
  };
  points: MapPointRecord[];
  total: number;
}
/**
 * A slide on the map, after geoprivacy: an obscured one at its public point, with its 0.2 degree cell.
 */
export interface MapPointRecord {
  id: string;
  lat: number;
  lon: number;
  obscured?: boolean;
  cell?: CellRecord | null;
}
/**
 * An annotation as the stage reads it: the W3C Web Annotation, who wrote it, and whether the reader may remove
 * it (its author, or a curator).
 */
export interface AnnotationRecord {
  id: string;
  asset_id: number;
  author: string;
  removable?: boolean;
  annotation: {
    [k: string]: unknown;
  };
}
/**
 * A contributor's case to reopen (``GET /api/slide-cases/{id}``): its summary and the case as last sent.
 */
export interface CaseRecord {
  id: string;
  status: "draft" | "processing" | "published" | "hidden";
  status_reason?: string | null;
  name: string;
  placement: string;
  updated_at: string;
  images?: CaseImageRecord[];
  submission?: {
    [k: string]: unknown;
  };
}
/**
 * An image of a contributor's case: its state, and its file's (the last upload).
 */
export interface CaseImageRecord {
  asset_id: number;
  token?: string | null;
  family: "macro" | "micro";
  role: string;
  status: "pending" | "ready" | "failed";
  failure?: string | null;
  has_file?: boolean;
  upload_status?: string | null;
  upload_reason?: string | null;
  upload_job?: string | null;
}
/**
 * A contributor's slide case in their list (``GET /api/slide-cases``).
 */
export interface CaseSummary {
  id: string;
  status: "draft" | "processing" | "published" | "hidden";
  status_reason?: string | null;
  name: string;
  placement: string;
  updated_at: string;
  images?: CaseImageRecord[];
}
export interface IdentificationList {
  community: CommunityRecord;
  identifications: IdentificationRecord[];
}
/**
 * How the identifications agree (R-088): the node, its anchor when Laminario can name it, and every score.
 */
export interface CommunityRecord {
  node?: string | null;
  anchor?: AnchorRecord | null;
  identifications: number;
  score?: number | null;
  cutoff: number;
  scores?: NodeScoreRecord[];
  as_good_as_it_can_be?: number;
  needs_more?: number;
  my_vote?: boolean | null;
  badge: "verified" | "needs_id" | "reference";
}
export interface NodeScoreRecord {
  node: string;
  depth: number;
  cumulative: number;
  disagreements: number;
  ancestor_disagreements: number;
  score: number;
}
/**
 * An identification on a slide, as a viewer may see it (``GET /api/slides/{id}/identifications``).
 */
export interface IdentificationRecord {
  id: string;
  anchor: AnchorRecord;
  node: string;
  by?: string | null;
  by_handle?: string | null;
  source?: boolean;
  mine?: boolean;
  body?: string | null;
  disagreement?: boolean | null;
  current: boolean;
  hidden?: boolean;
  category?: ("leading" | "improving" | "supporting" | "maverick") | null;
  created_at: string;
}
/**
 * A flag as the curators see it (``GET /api/flags``).
 */
export interface FlagRecord {
  id: string;
  target_kind: "slide" | "identification" | "annotation";
  target_id: string;
  slide_id: string;
  slide_name: string;
  category: "spam" | "inappropriate" | "copyright" | "wrong" | "other";
  comment?: string | null;
  by?: string | null;
  created_at: string;
  resolved_by?: string | null;
  resolved_at?: string | null;
  resolution?: string | null;
  hidden?: boolean;
}
/**
 * A curator's hiding or restoring, with the reason.
 */
export interface ModerationActionRecord {
  action: "hide" | "unhide";
  target_kind: "slide" | "identification" | "annotation";
  target_id: string;
  slide_id: string;
  reason: string;
  by?: string | null;
  created_at: string;
}
/**
 * An account's profile (``GET /api/people/{handle}``): never its email.
 */
export interface ProfileRecord {
  handle: string;
  name: string;
  role: "contributor" | "identifier" | "curator" | "admin";
  joined: string;
  last_active?: string | null;
  slides: number;
  verified: number;
  by_collection?: {
    [k: string]: number;
  };
  identifications: number;
  categories?: {
    [k: string]: number;
  };
  annotations: number;
}
/**
 * One of an account's identifications, in its cabinet.
 */
export interface PersonIdentificationRecord {
  id: string;
  slide: SlideSummary;
  anchor: AnchorRecord;
  category?: ("leading" | "improving" | "supporting" | "maverick") | null;
  community: boolean;
  created_at: string;
}
/**
 * A label stock a sheet is printed on (``GET /api/labels/stocks``).
 */
export interface StockRecord {
  id: string;
  name: LocalisedText;
  kind: "plain" | "stock";
  page: "A4" | "Letter";
  width_mm: number;
  height_mm: number;
  columns: number;
  rows: number;
  per_sheet: number;
  source: string;
  warnings?: string[];
}
/**
 * ``GET /api/about``: the numbers, the sources and licences counted, the policy, and the credits.
 */
export interface AboutRecord {
  read_at: string;
  numbers: AboutNumbers;
  sources?: SourceCount[];
  licences?: LicenceCount[];
  policy?: {
    [k: string]: string[];
  };
  vocabularies?: CreditRecord[];
  map?: CreditRecord[];
  software?: CreditRecord[];
  fonts?: CreditRecord[];
}
/**
 * The collection counted when the page is read (R-1501).
 */
export interface AboutNumbers {
  slides: number;
  by_origin?: {
    [k: string]: number;
  };
  realms?: RealmCount[];
  wsi: number;
  images: number;
  countries: number;
  contributors: number;
  identifications: number;
}
/**
 * A realm's published slides, and each of its collections' (``life.insects``).
 */
export interface RealmCount {
  id: string;
  slides: number;
  collections?: {
    [k: string]: number;
  };
}
/**
 * Where images came from, with their count and licences (R-1502): a source of ``credits.json``, the
 * contributors (``contribution``), or ``other``.
 */
export interface SourceCount {
  id: string;
  name?: string | null;
  url?: string | null;
  terms?: string | null;
  slides: number;
  images: number;
  licences?: {
    [k: string]: number;
  };
}
export interface LicenceCount {
  uri: string;
  short: string;
  family: string;
  images: number;
}
/**
 * A vocabulary, a map layer, a piece of software or a font the collection stands on (R-1507).
 */
export interface CreditRecord {
  id: string;
  name: string;
  url: string;
  licence?: string | null;
  citation?: string | null;
  doi?: string | null;
  terms?: string | null;
}
