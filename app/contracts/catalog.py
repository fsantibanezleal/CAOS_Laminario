"""The catalog contract: the record the web reads for a slide and its assets.

A record is assembled from database rows by ``app.services.catalog``, never copied from a submission, and
geoprivacy is applied while it is built. The JSON Schema of these models is committed in ``contracts/`` and
mirrored in TypeScript, so any change here is visible to the web build.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FormatRecord(_Record):
    code: str
    width_mm: float
    height_mm: float


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


class PlacementRecord(_Record):
    node: str
    overridden: bool = False


class QualityCheckRecord(_Record):
    code: Literal["licence_and_provenance", "scale", "modality", "macro_and_micro"]
    passed: bool
    detail: str


class QualityRecord(_Record):
    #: verified needs community agreement (identifications); until then a slide is needs_id or reference.
    badge: Literal["verified", "needs_id", "reference"]
    checks: list[QualityCheckRecord]


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
    origin: Literal["base", "contribution"]


class SlidePage(_Record):
    items: list[SlideSummary]
    total: int
    offset: int
    limit: int


class ValidationFlag(_Record):
    code: str
    field: str
    message: str


class ValidationError(_Record):
    field: str
    message: str
    expected: str


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


class PlacementResult(_Record):
    """Where a slide belongs (``POST /api/placement``): the suggestion, and every node that accepts it."""

    anchor: AnchorRecord | None = None
    suggestion: str | None = None
    path: list[NodeRef] = []
    accepting: list[str] = []
    errors: list[ValidationError] = []
