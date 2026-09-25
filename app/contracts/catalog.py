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
