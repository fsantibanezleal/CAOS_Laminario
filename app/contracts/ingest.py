"""The ingestion contract: what a slide-case submission must satisfy before anything is stored.

Validation runs in two phases, and both report the field and the expected range:

1. **Structure** (Pydantic): types, enumerations, ranges, lengths, patterns and partial dates, each declared on
   its field with an ``expected`` text.
2. **Rules across fields** (``rule_errors``): things that depend on another field or on the submission's origin,
   such as a custom size being required for a custom format, a coverslip fitting inside its slide, the licence
   policy of the origin, or a polarised asset's modality matching its state.

Conditions that are worth knowing but not worth refusing are returned as flags (``submission_flags``).

``validate_submission`` runs everything and is what the API and the base-collection pipeline call.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Annotated, Any, Literal, get_args

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, ValidationError
from pydantic_core import PydanticCustomError

from app.contracts import licences
from app.contracts.errors import contract_errors

# --- vocabularies ----------------------------------------------------------------------------------------

SlideFormat = Literal["iso_76x26", "us_75x25", "petro_27x46", "us_2x3in", "custom"]
Coverslip = Literal["none", "18x18", "22x22", "22x40", "22x50", "24x50", "24x60", "custom"]
Preparation = Literal[
    "whole_mount", "section", "smear", "squash", "strew",
    "thin_section", "polished_section", "peel", "cast", "fluid_mount",
]
Modality = Literal[
    "brightfield", "darkfield", "phase_contrast", "dic", "polarised_ppl",
    "polarised_xpl", "reflected", "fluorescence", "sem_external",
]
AnchorKind = Literal["taxon", "rock", "mineral", "crystal", "material"]
Geoprivacy = Literal["open", "obscured", "private"]
TypeStatus = Literal[
    "holotype", "paratype", "allotype", "syntype", "lectotype", "paralectotype", "neotype", "topotype", "other",
]
Family = Literal["macro", "micro"]
MacroRole = Literal["slide_overview", "specimen", "place", "label"]
MicroRole = Literal["single", "pyramid", "z_plane", "polarised"]
Role = Literal["slide_overview", "specimen", "place", "label", "single", "pyramid", "z_plane", "polarised"]

#: Physical size of each slide format, as (width, height) in millimetres with the long side horizontal.
SLIDE_SIZES_MM: dict[str, tuple[float, float]] = {
    "iso_76x26": (76.0, 26.0),
    "us_75x25": (75.0, 25.0),
    "petro_27x46": (46.0, 27.0),
    "us_2x3in": (76.2, 50.8),
}
#: Coverslip sizes as (long side, short side) in millimetres.
COVERSLIP_SIZES_MM: dict[str, tuple[float, float]] = {
    "18x18": (18.0, 18.0),
    "22x22": (22.0, 22.0),
    "22x40": (40.0, 22.0),
    "22x50": (50.0, 22.0),
    "24x50": (50.0, 24.0),
    "24x60": (60.0, 24.0),
}
ROLES_BY_FAMILY: dict[str, tuple[str, ...]] = {"macro": get_args(MacroRole), "micro": get_args(MicroRole)}
MAX_PLANES_PER_STACK = 200


def _one_of(literal: Any) -> str:
    return "one of: " + ", ".join(get_args(literal))


def _expect(text: str) -> dict[str, str]:
    return {"expected": text}


DATE_EXPECTED = "a date YYYY, YYYY-MM or YYYY-MM-DD, from 1600 to today"


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _check_partial_date(value: str) -> str:
    if not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", value):
        raise PydanticCustomError("partial_date", "not a date in the form YYYY, YYYY-MM or YYYY-MM-DD",
                                  _expect(DATE_EXPECTED))
    parts = [int(p) for p in value.split("-")]
    year, month, day = parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1
    try:
        start = date(year, month, day)
    except ValueError:
        raise PydanticCustomError("partial_date", "{value} is not a calendar date",
                                  {"value": value, **_expect(DATE_EXPECTED)}) from None
    if year < 1600 or start > _today():
        raise PydanticCustomError("date_range", "{value} is outside 1600 to today",
                                  {"value": value, **_expect(DATE_EXPECTED)})
    return value


PartialDate = Annotated[str, AfterValidator(_check_partial_date)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- the slide ---------------------------------------------------------------------------------------------

class SizeMm(_Model):
    """A custom slide size."""

    w_mm: float = Field(ge=20, le=100, json_schema_extra=_expect("20 to 100 mm"))
    h_mm: float = Field(ge=20, le=100, json_schema_extra=_expect("20 to 100 mm"))


class CoverslipSizeMm(_Model):
    """A custom coverslip size."""

    w_mm: float = Field(gt=0, le=100, json_schema_extra=_expect("more than 0 and at most 100 mm"))
    h_mm: float = Field(gt=0, le=100, json_schema_extra=_expect("more than 0 and at most 100 mm"))


class SlideSpec(_Model):
    format: SlideFormat = Field(json_schema_extra=_expect(_one_of(SlideFormat)))
    custom_mm: SizeMm | None = Field(None, json_schema_extra=_expect("a size, only for the custom format"))
    coverslip: Coverslip = Field("none", json_schema_extra=_expect(_one_of(Coverslip)))
    coverslip_custom_mm: CoverslipSizeMm | None = Field(
        None, json_schema_extra=_expect("a size, only for a custom coverslip"))
    preparation: Preparation = Field(json_schema_extra=_expect(_one_of(Preparation)))
    stain: str | None = Field(None, max_length=80, json_schema_extra=_expect("at most 80 characters"))
    mountant: str | None = Field(None, max_length=80, json_schema_extra=_expect("at most 80 characters"))
    catalogue_number: str | None = Field(None, max_length=64, json_schema_extra=_expect("at most 64 characters"))
    label_note: str | None = Field(None, max_length=160, json_schema_extra=_expect("at most 160 characters"))
    prepared_on: PartialDate | None = Field(None, json_schema_extra=_expect(DATE_EXPECTED))
    preparer: str | None = Field(None, max_length=120, json_schema_extra=_expect("at most 120 characters"))


# --- the specimen --------------------------------------------------------------------------------------------

class Anchor(_Model):
    """What the slide shows: a taxon, a rock, a mineral, a crystal or a material."""

    kind: AnchorKind = Field(json_schema_extra=_expect(_one_of(AnchorKind)))
    ref: str = Field(min_length=1, max_length=200,
                     json_schema_extra=_expect("1 to 200 characters; for a taxon, its GBIF usage key"))
    name: str = Field(min_length=1, max_length=200, json_schema_extra=_expect("1 to 200 characters"))
    rank: str | None = Field(None, max_length=32, json_schema_extra=_expect("at most 32 characters"))


class Coordinates(_Model):
    lat: float = Field(ge=-90, le=90, json_schema_extra=_expect("-90 to 90 degrees"))
    lon: float = Field(ge=-180, le=180, json_schema_extra=_expect("-180 to 180 degrees"))
    uncertainty_m: float | None = Field(None, ge=0, json_schema_extra=_expect("at least 0 m"))


class SpecimenSpec(_Model):
    anchor: Anchor
    collected_on: PartialDate | None = Field(None, json_schema_extra=_expect(DATE_EXPECTED))
    collector: str | None = Field(None, max_length=120, json_schema_extra=_expect("at most 120 characters"))
    locality_text: str | None = Field(None, max_length=300, json_schema_extra=_expect("at most 300 characters"))
    coordinates: Coordinates | None = None
    geoprivacy: Geoprivacy = Field("open", json_schema_extra=_expect(_one_of(Geoprivacy)))
    host: Anchor | None = Field(None, json_schema_extra=_expect("a taxon anchor"))
    type_status: TypeStatus | None = Field(None, json_schema_extra=_expect(_one_of(TypeStatus)))


# --- placement ------------------------------------------------------------------------------------------------

NODE_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)*$"


class PlacementSpec(_Model):
    node: str = Field(max_length=120, pattern=NODE_PATTERN,
                      json_schema_extra=_expect("a node id: lowercase words joined by hyphens, levels by dots"))
    override_reason: str | None = Field(None, max_length=300, json_schema_extra=_expect("at most 300 characters"))


# --- assets ---------------------------------------------------------------------------------------------------

class PlaneSpec(_Model):
    index: int = Field(ge=0, le=10000, json_schema_extra=_expect("0 to 10000"))
    depth_um: float = Field(ge=-100000, le=100000, json_schema_extra=_expect("-100000 to 100000 um"))
    stack: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$",
                       json_schema_extra=_expect("1 to 64 letters, digits, hyphens or underscores"))


class PolarisationSpec(_Model):
    state: Literal["ppl", "xpl"] = Field(json_schema_extra=_expect("one of: ppl, xpl"))
    angle_deg: float = Field(0.0, ge=0, le=360, json_schema_extra=_expect("0 to 360 degrees"))


class SourceSpec(_Model):
    """Where an imported asset came from (the base collection)."""

    url: HttpUrl = Field(json_schema_extra=_expect("an http or https URL"))
    record_id: str = Field(min_length=1, max_length=200, json_schema_extra=_expect("1 to 200 characters"))
    retrieved_on: date = Field(json_schema_extra=_expect("a date YYYY-MM-DD, not in the future"))
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$", json_schema_extra=_expect("64 lowercase hexadecimal characters"))


class ExifSpec(_Model):
    """What the browser read from a photo's EXIF block, sent so the server can flag and strip."""

    datetime_original: datetime | None = Field(None, json_schema_extra=_expect("an ISO date-time"))
    gps_present: bool = False


class AssetSpec(_Model):
    family: Family = Field(json_schema_extra=_expect("one of: macro, micro"))
    role: Role = Field(json_schema_extra=_expect(_one_of(Role)))
    upload_id: str | None = Field(None, pattern=r"^[A-Za-z0-9_+-]{8,128}$",
                                  json_schema_extra=_expect("an upload id, 8 to 128 characters"))
    remote_iiif: HttpUrl | None = Field(None, json_schema_extra=_expect("the URL of a IIIF Image API service"))
    source: SourceSpec | None = None
    licence: str = Field(min_length=1, max_length=200, json_schema_extra=_expect("a licence URI"))
    rights_holder: str | None = Field(None, max_length=200, json_schema_extra=_expect("at most 200 characters"))
    creator: str | None = Field(None, max_length=200, json_schema_extra=_expect("at most 200 characters"))
    pixel_size_um: float | None = Field(None, ge=0.05, le=50, json_schema_extra=_expect("0.05 to 50 um per pixel"))
    modality: Modality | None = Field(None, json_schema_extra=_expect(_one_of(Modality)))
    plane: PlaneSpec | None = None
    polarisation: PolarisationSpec | None = None
    exif: ExifSpec | None = None
    caption: str | None = Field(None, max_length=300, json_schema_extra=_expect("at most 300 characters"))


# --- the submission -------------------------------------------------------------------------------------------

class SlideCaseSubmission(_Model):
    origin: Literal["contribution", "base"] = Field(
        "contribution", json_schema_extra=_expect("one of: contribution, base"))
    slide: SlideSpec
    specimen: SpecimenSpec
    placement: PlacementSpec
    assets: list[AssetSpec] = Field(min_length=1, max_length=500, json_schema_extra=_expect("1 to 500 assets"))


# --- rules across fields -----------------------------------------------------------------------------------------

@dataclass
class Issue:
    field: str
    message: str
    expected: str

    def as_dict(self) -> dict[str, str]:
        return {"field": self.field, "message": self.message, "expected": self.expected}


@dataclass
class Flag:
    code: str
    field: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}


def slide_size_mm(slide: SlideSpec) -> tuple[float, float] | None:
    """Physical (width, height) of a slide in millimetres, long side first."""
    if slide.format == "custom":
        if slide.custom_mm is None:
            return None
        w, h = slide.custom_mm.w_mm, slide.custom_mm.h_mm
        return (max(w, h), min(w, h))
    return SLIDE_SIZES_MM[slide.format]


def coverslip_size_mm(slide: SlideSpec) -> tuple[float, float] | None:
    """Physical (long, short) of the coverslip in millimetres; ``None`` when there is none."""
    if slide.coverslip == "none":
        return None
    if slide.coverslip == "custom":
        if slide.coverslip_custom_mm is None:
            return None
        w, h = slide.coverslip_custom_mm.w_mm, slide.coverslip_custom_mm.h_mm
        return (max(w, h), min(w, h))
    return COVERSLIP_SIZES_MM[slide.coverslip]


def rule_errors(sub: SlideCaseSubmission) -> list[Issue]:
    """Every rule that involves more than one field or the submission's origin."""
    issues: list[Issue] = []
    s = sub.slide

    if s.format == "custom" and s.custom_mm is None:
        issues.append(Issue("slide.custom_mm", "a custom format needs its size", "a width and height, 20 to 100 mm"))
    if s.format != "custom" and s.custom_mm is not None:
        issues.append(Issue("slide.custom_mm", "a size is given for a standard format",
                            "no size unless the format is custom"))
    if s.coverslip == "custom" and s.coverslip_custom_mm is None:
        issues.append(Issue("slide.coverslip_custom_mm", "a custom coverslip needs its size",
                            "a width and height in mm"))
    if s.coverslip != "custom" and s.coverslip_custom_mm is not None:
        issues.append(Issue("slide.coverslip_custom_mm", "a size is given for a standard coverslip",
                            "no size unless the coverslip is custom"))
    slide_mm, cover_mm = slide_size_mm(s), coverslip_size_mm(s)
    if slide_mm and cover_mm and (cover_mm[0] > slide_mm[0] or cover_mm[1] > slide_mm[1]):
        field_name = "slide.coverslip_custom_mm" if s.coverslip == "custom" else "slide.coverslip"
        issues.append(Issue(field_name, "the coverslip does not fit on the slide",
                            f"a coverslip within {slide_mm[0]:g} x {slide_mm[1]:g} mm"))

    anchor = sub.specimen.anchor
    if anchor.kind == "taxon" and not anchor.ref.isdigit():
        issues.append(Issue("specimen.anchor.ref", "a taxon is referenced by its GBIF usage key",
                            "the GBIF usage key, digits only"))
    host = sub.specimen.host
    if host is not None:
        if host.kind != "taxon":
            issues.append(Issue("specimen.host.kind", "a host is an organism", "taxon"))
        elif not host.ref.isdigit():
            issues.append(Issue("specimen.host.ref", "a taxon is referenced by its GBIF usage key",
                                "the GBIF usage key, digits only"))

    stacks: Counter[str] = Counter()
    for i, a in enumerate(sub.assets):
        at = f"assets.{i}"
        if a.role not in ROLES_BY_FAMILY[a.family]:
            issues.append(Issue(f"{at}.role", f"{a.role} is not a {a.family} role",
                                "one of: " + ", ".join(ROLES_BY_FAMILY[a.family])))
        contents = [name for name, value in (("upload_id", a.upload_id), ("remote_iiif", a.remote_iiif),
                                              ("source", a.source)) if value is not None]
        if sub.origin == "base" and a.source is None:
            issues.append(Issue(f"{at}.source", "a base-collection asset needs its source",
                                "url, record_id, retrieved_on and sha256"))
        elif sub.origin == "contribution" and a.source is not None:
            issues.append(Issue(f"{at}.source", "a contribution carries an upload or a remote service, not a source",
                                "upload_id or remote_iiif"))
        elif sub.origin == "contribution" and len(contents) != 1:
            issues.append(Issue(f"{at}.upload_id", "an asset needs exactly one content",
                                "exactly one of upload_id or remote_iiif"))
        if a.source is not None and a.source.retrieved_on > _today():
            issues.append(Issue(f"{at}.source.retrieved_on", "the retrieval date is in the future",
                                "a date YYYY-MM-DD, not in the future"))
        if not licences.allowed(a.licence, sub.origin):
            issues.append(Issue(f"{at}.licence", f"{a.licence} is not accepted for a {sub.origin} asset",
                                licences.expectation(sub.origin)))
        if not (a.rights_holder or a.creator):
            issues.append(Issue(f"{at}.rights_holder", "an asset needs a rights holder or a creator",
                                "a rights holder or a creator"))
        if a.family == "micro" and a.modality is None:
            issues.append(Issue(f"{at}.modality", "a micro asset needs its imaging modality", _one_of(Modality)))
        if a.role == "z_plane":
            if a.plane is None:
                issues.append(Issue(f"{at}.plane", "a focal plane needs its index, depth and stack",
                                    "index, depth_um and stack"))
            else:
                stacks[a.plane.stack] += 1
        elif a.plane is not None:
            issues.append(Issue(f"{at}.plane", "only a z_plane asset carries a plane", "no plane"))
        if a.role == "polarised":
            if a.polarisation is None:
                issues.append(Issue(f"{at}.polarisation", "a polarised asset needs its state and angle",
                                    "state ppl or xpl, angle 0 to 360 degrees"))
            else:
                wanted = "polarised_ppl" if a.polarisation.state == "ppl" else "polarised_xpl"
                if a.modality != wanted:
                    issues.append(Issue(f"{at}.modality", "the modality does not match the polarisation state",
                                        wanted))
        elif a.polarisation is not None:
            issues.append(Issue(f"{at}.polarisation", "only a polarised asset carries a polarisation",
                                "no polarisation"))
    for stack, count in stacks.items():
        if count > MAX_PLANES_PER_STACK:
            issues.append(Issue("assets", f"stack {stack} has {count} planes",
                                f"at most {MAX_PLANES_PER_STACK} planes per stack"))
    return issues


def submission_flags(sub: SlideCaseSubmission) -> list[Flag]:
    """Conditions that are accepted but reported."""
    flags: list[Flag] = []
    collected = sub.specimen.collected_on
    collected_day = date.fromisoformat(collected) if collected and len(collected) == 10 else None
    for i, a in enumerate(sub.assets):
        at = f"assets.{i}"
        if a.family == "micro" and a.pixel_size_um is None:
            flags.append(Flag("not_to_scale", f"{at}.pixel_size_um",
                              "no pixel size: the image is shown without a scale bar and not to scale"))
        if a.exif is not None:
            if a.exif.gps_present and sub.specimen.geoprivacy == "private":
                flags.append(Flag("gps_stripped", f"{at}.exif.gps_present",
                                  "the photo carries GPS and the place is private: the GPS is removed before storage"))
            shot = a.exif.datetime_original
            if collected_day and shot and abs((shot.date() - collected_day).days) > 1:
                flags.append(Flag("exif_date_mismatch", f"{at}.exif.datetime_original",
                                  f"the photo was taken on {shot.date()}, the specimen collected on {collected_day}"))
    return flags


@dataclass
class ValidationReport:
    submission: SlideCaseSubmission | None
    errors: list[dict[str, str]] = field(default_factory=list)
    flags: list[dict[str, str]] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.submission is not None and not self.errors


def validate_submission(payload: Any) -> ValidationReport:
    """Run the whole ingestion contract on a raw payload."""
    try:
        sub = SlideCaseSubmission.model_validate(payload)
    except ValidationError as exc:
        return ValidationReport(None, contract_errors(exc, SlideCaseSubmission))
    errors = [issue.as_dict() for issue in rule_errors(sub)]
    flags = [flag.as_dict() for flag in submission_flags(sub)]
    return ValidationReport(sub, errors, flags if not errors else [])
