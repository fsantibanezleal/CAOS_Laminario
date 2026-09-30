"""The catalog contract: the record the web reads for a slide and its assets.

A record is assembled from database rows by ``app.services.catalog``, never copied from a submission, and
geoprivacy is applied while it is built. The JSON Schema of these models is committed in ``contracts/`` and
mirrored in TypeScript, so any change here is visible to the web build.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FormatRecord(_Record):
    code: str
    width_mm: float
    height_mm: float
    #: The source did not record the physical slide; the format is the standard one, shown as assumed.
    assumed: bool = False


class CoverslipRecord(_Record):
    code: str
    long_mm: float
    short_mm: float


class AnchorRecord(_Record):
    kind: Literal["taxon", "rock", "mineral", "crystal", "material"]
    ref: str
    name: str
    rank: str | None = None
    #: The Nickel-Strunz code of a mineral or the snow-crystal category of an ice crystal.
    classification: str | None = None


class LabelRecord(_Record):
    """What the printed label shows."""

    name: str
    catalogue_number: str | None = None
    preparation: str
    stain: str | None = None
    mountant: str | None = None
    label_note: str | None = None
    prepared_on: str | None = None
    preparer: str | None = None
    collected_on: str | None = None
    collector: str | None = None
    locality_text: str | None = None
    type_status: str | None = None


class PointRecord(_Record):
    lat: float
    lon: float


class CellRecord(_Record):
    south: float
    west: float
    north: float
    east: float


class PlaceRecord(_Record):
    """Where the specimen was collected, after geoprivacy."""

    geoprivacy: Literal["open", "obscured", "private"]
    point: PointRecord | None = None
    cell: CellRecord | None = None
    uncertainty_m: float | None = None
    locality_text: str | None = None
    #: ISO 3166-1 alpha-2. Like the locality text it is kept for a private place (only coordinates are withheld).
    country: str | None = None


class SummaryLabel(_Record):
    """What a drawer shows on a slide's label end (no coordinates, so nothing geoprivacy withholds)."""

    catalogue_number: str | None = None
    collected_on: str | None = None
    locality_text: str | None = None
    country: str | None = None


class PlacementRecord(_Record):
    node: str
    overridden: bool = False


class QualityCheckRecord(_Record):
    code: Literal["licence_and_provenance", "scale", "modality", "macro_and_micro"]
    passed: bool
    detail: str


class QualityRecord(_Record):
    #: verified: every check passes and the identifications agree as far as the anchor's kind needs (U13);
    #: reference: a check fails, or the community said an anchor too coarse is as good as it can be; else needs_id.
    badge: Literal["verified", "needs_id", "reference"]
    checks: list[QualityCheckRecord]
    #: The node the identifications agree on (a lineage node id such as taxon:1032608), and its rank for a taxon.
    community_node: str | None = None
    community_rank: str | None = None


class LicenceRecord(_Record):
    uri: str
    short_name: str


class SourceRecord(_Record):
    url: str
    record_id: str
    retrieved_on: date
    sha256: str


class MediaRecord(_Record):
    kind: Literal["pyramid", "image", "remote_iiif"]
    #: The IIIF Image API info.json of a pyramid or a remote service.
    iiif_info_url: str | None = None
    #: A plain image file (macro photos that are not pyramids).
    image_url: str | None = None
    #: IIIF Image API version of the service at ``iiif_info_url`` (3 for this deployment's own pyramids).
    iiif_version: Literal[2, 3] | None = None
    width_px: int | None = None
    height_px: int | None = None


class PlaneRecord(_Record):
    stack: str
    index: int
    depth_um: float


class PolarisationRecord(_Record):
    state: Literal["ppl", "xpl"]
    angle_deg: float


class AssetRecord(_Record):
    id: int
    family: Literal["macro", "micro"]
    role: str
    sort_order: int
    status: Literal["pending", "ready", "failed"]
    media: MediaRecord
    pixel_size_um: float | None = None
    modality: str | None = None
    plane: PlaneRecord | None = None
    polarisation: PolarisationRecord | None = None
    caption: str | None = None
    licence: LicenceRecord
    rights_holder: str | None = None
    creator: str | None = None
    source: SourceRecord | None = None
    #: The SHA-256 of the file the image was made from: the source's for the base collection, the verified
    #: upload's for a contribution, so anyone holding the file can check it is the one shown.
    original_sha256: str | None = None


class PersonRef(_Record):
    """An account as others may see it: its handle and display name, never its email (U14)."""

    handle: str
    name: str


class SlideRecord(_Record):
    #: The short id, upper case: the label, the permalink and the QR code all carry it.
    id: str
    permalink: str
    #: The permalink in upper case, the form encoded in the QR (alphanumeric mode).
    qr_payload: str
    status: Literal["draft", "processing", "published", "hidden"]
    origin: Literal["base", "contribution"]
    format: FormatRecord
    coverslip: CoverslipRecord | None = None
    label: LabelRecord
    anchor: AnchorRecord
    host: AnchorRecord | None = None
    #: The part of the organism the slide shows, and whether the specimen is recent, fossil or in amber.
    part: str | None = None
    preservation: Literal["recent", "fossil", "in_amber"] = "recent"
    place: PlaceRecord
    placement: PlacementRecord
    quality: QualityRecord
    assets: list[AssetRecord]
    manifest_url: str
    #: Who contributed the slide (U14); None for the base collection.
    contributor: PersonRef | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class SlideSummary(_Record):
    """A slide in a list: enough to draw it in a drawer."""

    id: str
    permalink: str
    anchor: AnchorRecord
    format: FormatRecord
    placement: PlacementRecord
    preparation: str
    thumbnail_url: str | None = None
    #: A photograph of the whole glass slide (a slide overview, taken or kept by a scanner), when one exists: the
    #: interface then shows the slide as that photograph, its real glass, instead of drawing it (U17).
    glass_photo_url: str | None = None
    origin: Literal["base", "contribution"]
    label: SummaryLabel = SummaryLabel()


class SlidePage(_Record):
    items: list[SlideSummary]
    total: int
    offset: int
    limit: int


class CaseImageRecord(_Record):
    """An image of a contributor's case: its state, and its file's (the last upload)."""

    asset_id: int
    token: str | None = None
    family: Literal["macro", "micro"]
    role: str
    status: Literal["pending", "ready", "failed"]
    failure: str | None = None
    has_file: bool = False
    upload_status: str | None = None
    upload_reason: str | None = None
    upload_job: str | None = None


class CaseSummary(_Record):
    """A contributor's slide case in their list (``GET /api/slide-cases``)."""

    id: str
    status: Literal["draft", "processing", "published", "hidden"]
    status_reason: str | None = None
    name: str
    placement: str
    updated_at: datetime
    images: list[CaseImageRecord] = []


class CaseRecord(CaseSummary):
    """A contributor's case to reopen (``GET /api/slide-cases/{id}``): its summary and the case as last sent."""

    submission: dict[str, Any] = {}


class AnnotationRecord(_Record):
    """An annotation as the stage reads it: the W3C Web Annotation, who wrote it, and whether the reader may remove
    it (its author, or a curator)."""

    id: str
    asset_id: int
    author: str
    removable: bool = False
    annotation: dict[str, Any]


class FacetCounts(_Record):
    """For each facet, its values under the current filters and how many slides each would match (the facet's own
    filter left out, so a second value shows what it adds)."""

    collection: dict[str, int] = {}
    kind: dict[str, int] = {}
    preparation: dict[str, int] = {}
    modality: dict[str, int] = {}
    preservation: dict[str, int] = {}
    country: dict[str, int] = {}
    licence: dict[str, int] = {}
    wsi: dict[str, int] = {}
    origin: dict[str, int] = {}


class MapPointRecord(_Record):
    """A slide on the map, after geoprivacy: an obscured one at its public point, with its 0.2 degree cell."""

    id: str
    lat: float
    lon: float
    obscured: bool = False
    cell: CellRecord | None = None


class MapRecord(_Record):
    countries: dict[str, int]
    points: list[MapPointRecord]
    total: int


class ValidationFlag(_Record):
    code: str
    field: str
    message: str
    params: dict[str, str] = {}


class ValidationError(_Record):
    """A reason a slide case is refused: the field, the API's message and what would be accepted, and a stable code
    with the values the message names, so an interface can say it in its own words (R-1202)."""

    field: str
    message: str
    expected: str
    code: str | None = None
    params: dict[str, str] = {}


class ValidationResult(_Record):
    """The answer of ``POST /api/slide-cases/validate``."""

    valid: bool
    flags: list[ValidationFlag] = []
    errors: list[ValidationError] = []


class JobRecord(_Record):
    """A processing job as ``GET /api/jobs/{id}`` returns it."""

    id: str
    kind: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    attempts: int
    error: str | None = None
    result: dict | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    #: The event stream of this job (Server-Sent Events, replayable with ``Last-Event-ID``).
    events_url: str


class JobEventRecord(_Record):
    """One Server-Sent Event of a job's stream: its ``id`` field is ``seq``, its ``event`` field ``event``."""

    seq: int
    event: Literal["queued", "started", "progress", "log", "requeued", "succeeded", "failed", "cancelled"]
    data: dict
    at: datetime


class AccountRecord(_Record):
    """An account as ``GET /api/users/me`` returns it."""

    id: str
    email: str
    display_name: str
    role: Literal["contributor", "identifier", "curator", "admin"]
    is_active: bool
    is_verified: bool
    #: The public address of the account's profile (U14).
    handle: str | None = None


class InvitationRecord(_Record):
    """An invitation as its issuer sees it. ``link`` is present only in the answer that created it, and only
    when it was not mailed: the token is never stored, so it cannot be shown again."""

    id: int
    email: str | None = None
    role: Literal["contributor", "identifier", "curator", "admin"]
    note: str | None = None
    status: Literal["pending", "used", "expired", "revoked"]
    created_at: datetime
    expires_at: datetime
    mailed: bool
    link: str | None = None


class CreatedSlideCase(_Record):
    """The answer of ``POST /api/slide-cases``: the new draft and the flags of its submission."""

    id: str
    status: str
    flags: list[ValidationFlag] = []


class UploadRecord(_Record):
    """An upload as its contributor sees it (``GET /api/uploads``)."""

    id: int
    slide_id: str
    asset_id: int
    filename: str | None = None
    size: int
    wsi: bool
    status: Literal["uploading", "received", "accepted", "rejected", "cancelled"]
    #: What the bytes are, once verified (``jpeg``, ``tiff``, ``zip-mrxs``, ...).
    sniffed: str | None = None
    sha256: str | None = None
    #: Why it was refused, naming what was found and what is accepted.
    reason: str | None = None
    #: The processing job, once the file was accepted (its event stream is ``/api/jobs/{id}/events``).
    job_id: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class LocalisedText(_Record):
    en: str
    es: str


class DefinitionRecord(_Record):
    """One condition of a node's rule, for people: a taxon with its GBIF page, a rock family, a part."""

    kind: Literal["taxon", "excluded-taxon", "kind", "rock", "mineral", "crystal", "material", "part",
                  "preservation", "relation"]
    value: str
    label: str
    url: str | None = None


class CollectionNodeRecord(_Record):
    """A node of the collection tree (``GET /api/collections``), with its published slides counted."""

    id: str
    level: Literal["realm", "collection", "sub-collection", "group"]
    name: LocalisedText
    about: LocalisedText
    #: The symbol id in the icon sprite.
    icon: str
    #: A view (Parasites and hosts) lists slides placed elsewhere; nothing is placed in it.
    view: bool = False
    priority: int = 0
    #: The conditions of the node's rule; a node without any takes what its children take.
    defined_by: list[DefinitionRecord] = []
    #: Published slides placed at this node or below (for a view, the slides it shows).
    slide_count: int = 0
    children: list[CollectionNodeRecord] = []


class NodeRef(_Record):
    id: str
    name: LocalisedText
    icon: str


class CollectionTreeRecord(_Record):
    """The whole tree: the three realms and everything under them."""

    realms: list[CollectionNodeRecord]
    #: Realms, collections, and sub-collections and groups (each shared set counted once).
    counts: dict[str, int]


class CollectionNodeDetail(_Record):
    """One node (``GET /api/collections/{id}``): itself with its children, and the path down to it."""

    node: CollectionNodeRecord
    path: list[NodeRef]
    iiif_collection_url: str


class FacetValueRecord(_Record):
    id: str
    name: LocalisedText
    icon: str


class FacetRecord(_Record):
    """A property that cuts across the tree, with the icon of each value."""

    id: Literal["preparation", "modality", "plant-organ", "crystal-system"]
    name: LocalisedText
    values: list[FacetValueRecord]


class AnchorSuggestion(_Record):
    """A name the anchor field can offer (``GET /api/anchors/search``)."""

    ref: str
    name: str
    rank: str | None = None
    classification: str | None = None
    #: For a taxon, its higher classification (kingdom to family).
    context: str | None = None


class PartRecord(_Record):
    """A part of an organism the part field offers (``GET /api/vocab/parts``), with its organ system."""

    id: str
    group: str
    name: LocalisedText


class PlacementResult(_Record):
    """Where a slide belongs (``POST /api/placement``): the suggestion, and every node that accepts it."""

    anchor: AnchorRecord | None = None
    suggestion: str | None = None
    path: list[NodeRef] = []
    accepting: list[str] = []
    errors: list[ValidationError] = []


# --- the community (U13) ------------------------------------------------------------------------------------------

class IdentificationRecord(_Record):
    """An identification on a slide, as a viewer may see it (``GET /api/slides/{id}/identifications``)."""

    id: str
    anchor: AnchorRecord
    #: The lineage node it names (``taxon:1032608``, ``rock:igneous.coarse/granite``).
    node: str
    #: The account's display name; None for the source's determination of a base slide.
    by: str | None = None
    #: The account's handle, the address of its profile (U14).
    by_handle: str | None = None
    source: bool = False
    mine: bool = False
    body: str | None = None
    #: For an identification of an ancestor of the slide's anchor: whether it disagreed with the finer one.
    disagreement: bool | None = None
    current: bool
    hidden: bool = False
    #: leading, improving, supporting or maverick (iNaturalist's categories), for a current visible identification.
    category: Literal["leading", "improving", "supporting", "maverick"] | None = None
    created_at: datetime


class NodeScoreRecord(_Record):
    node: str
    depth: int
    cumulative: int
    disagreements: int
    ancestor_disagreements: int
    score: float


class CommunityRecord(_Record):
    """How the identifications agree (R-088): the node, its anchor when Laminario can name it, and every score."""

    node: str | None = None
    anchor: AnchorRecord | None = None
    #: How many current, visible identifications counted.
    identifications: int
    #: The community node's score, and the cutoff it had to exceed.
    score: float | None = None
    cutoff: float
    scores: list[NodeScoreRecord] = Field(default_factory=list)
    as_good_as_it_can_be: int = 0
    needs_more: int = 0
    #: The signed-in account's own vote, if any.
    my_vote: bool | None = None
    badge: Literal["verified", "needs_id", "reference"]


class IdentificationList(_Record):
    community: CommunityRecord
    identifications: list[IdentificationRecord]


class FlagRecord(_Record):
    """A flag as the curators see it (``GET /api/flags``)."""

    id: str
    target_kind: Literal["slide", "identification", "annotation"]
    target_id: str
    slide_id: str
    slide_name: str
    category: Literal["spam", "inappropriate", "copyright", "wrong", "other"]
    comment: str | None = None
    by: str | None = None
    created_at: datetime
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    resolution: str | None = None
    #: Whether the flagged item is hidden now.
    hidden: bool = False


class ModerationActionRecord(_Record):
    """A curator's hiding or restoring, with the reason."""

    action: Literal["hide", "unhide"]
    target_kind: Literal["slide", "identification", "annotation"]
    target_id: str
    slide_id: str
    reason: str
    by: str | None = None
    created_at: datetime


# --- the profile and the label sheets (U14) ----------------------------------------------------------------------

class ProfileRecord(_Record):
    """An account's profile (``GET /api/people/{handle}``): never its email."""

    handle: str
    name: str
    role: Literal["contributor", "identifier", "curator", "admin"]
    joined: datetime
    #: Its newest published slide or identification.
    last_active: datetime | None = None
    slides: int
    verified: int
    #: Published slides by collection (``life.insects``).
    by_collection: dict[str, int] = Field(default_factory=dict)
    #: Current visible identifications of others' slides, and by category.
    identifications: int
    categories: dict[str, int] = Field(default_factory=dict)
    annotations: int


class PersonIdentificationRecord(_Record):
    """One of an account's identifications, in its cabinet."""

    id: str
    slide: SlideSummary
    anchor: AnchorRecord
    category: Literal["leading", "improving", "supporting", "maverick"] | None = None
    #: Whether it names the slide's community anchor now.
    community: bool
    created_at: datetime


class StockRecord(_Record):
    """A label stock a sheet is printed on (``GET /api/labels/stocks``)."""

    id: str
    name: LocalisedText
    kind: Literal["plain", "stock"]
    page: Literal["A4", "Letter"]
    width_mm: float
    height_mm: float
    columns: int
    rows: int
    per_sheet: int
    source: str
    warnings: list[str] = Field(default_factory=list)


# --- About the collection (U15) --------------------------------------------------------------------------------------

class RealmCount(_Record):
    """A realm's published slides, and each of its collections' (``life.insects``)."""

    id: str
    slides: int
    collections: dict[str, int] = Field(default_factory=dict)


class AboutNumbers(_Record):
    """The collection counted when the page is read (R-1501)."""

    slides: int
    #: ``base`` and ``contribution``.
    by_origin: dict[str, int] = Field(default_factory=dict)
    realms: list[RealmCount] = Field(default_factory=list)
    #: Slides with a whole-slide scan (a pyramid or a focal stack of one).
    wsi: int
    #: Source images of published slides: a focal plane counts, a fused composite does not.
    images: int
    countries: int
    #: Accounts with a published slide.
    contributors: int
    #: Current visible identifications by accounts of slides they did not contribute.
    identifications: int


class SourceCount(_Record):
    """Where images came from, with their count and licences (R-1502): a source of ``credits.json``, the
    contributors (``contribution``), or ``other``."""

    id: str
    name: str | None = None
    url: str | None = None
    terms: str | None = None
    slides: int
    images: int
    #: Canonical licence URI to its count of images.
    licences: dict[str, int] = Field(default_factory=dict)


class LicenceCount(_Record):
    uri: str
    short: str
    #: cc0, pdm, nkc, by, by-sa, by-nc, by-nc-sa.
    family: str
    images: int


class CreditRecord(_Record):
    """A vocabulary, a map layer, a piece of software or a font the collection stands on (R-1507)."""

    id: str
    name: str
    url: str
    #: A licence URI or SPDX identifier; None when the source states none (names used as facts).
    licence: str | None = None
    citation: str | None = None
    doi: str | None = None
    terms: str | None = None


class AboutRecord(_Record):
    """``GET /api/about``: the numbers, the sources and licences counted, the policy, and the credits."""

    read_at: datetime
    numbers: AboutNumbers
    sources: list[SourceCount] = Field(default_factory=list)
    licences: list[LicenceCount] = Field(default_factory=list)
    #: The licence families the policy accepts, by origin (``base``, ``contribution``).
    policy: dict[str, list[str]] = Field(default_factory=dict)
    vocabularies: list[CreditRecord] = Field(default_factory=list)
    map: list[CreditRecord] = Field(default_factory=list)
    software: list[CreditRecord] = Field(default_factory=list)
    fonts: list[CreditRecord] = Field(default_factory=list)
