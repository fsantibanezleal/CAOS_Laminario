"""Build catalog records from database rows: geoprivacy, media addresses, quality checks.

The builder is the only place a slide leaves the database for the web, so the privacy rule lives here:
an obscured place is reduced to its 0.2 degree cell and a stable public point inside it; a private place
carries neither point nor cell.
"""

from __future__ import annotations

import hashlib
import math
from urllib.parse import quote

from app.config import Settings
from app.contracts import catalog as c
from app.contracts import licences
from app.db.models import Asset, Slide

CELL_DEGREES = 0.2
#: Images made from other images of the slide (U2's fusion of a focal stack).
DERIVED_ROLES = ("edf_wavelet", "edf_variance", "height_map")


def obscure(short_id: str, lat: float, lon: float) -> tuple[c.PointRecord, c.CellRecord]:
    """The 0.2 degree cell containing (lat, lon) and a public point inside it, fixed for this slide.

    The public point depends only on the cell and the short id, never on where the true point lies inside
    the cell, so two requests (or two slides at the same place) cannot be combined to narrow it down.
    """
    south = math.floor(lat / CELL_DEGREES) * CELL_DEGREES
    west = math.floor(lon / CELL_DEGREES) * CELL_DEGREES
    digest = hashlib.sha256(short_id.encode("ascii")).digest()
    u = int.from_bytes(digest[:8], "big") / 2**64
    v = int.from_bytes(digest[8:16], "big") / 2**64
    north, east = south + CELL_DEGREES, west + CELL_DEGREES
    point_lat = min(90.0, max(-90.0, south + CELL_DEGREES * u))
    point_lon = west + CELL_DEGREES * v
    cell = c.CellRecord(
        south=round(max(-90.0, south), 6), west=round(west, 6),
        north=round(min(90.0, north), 6), east=round(east, 6),
    )
    return c.PointRecord(lat=round(point_lat, 6), lon=round(point_lon, 6)), cell


def place_record(slide: Slide) -> c.PlaceRecord:
    # A private place keeps its locality text and country (both coarser than a point); only coordinates are withheld.
    base = {"geoprivacy": slide.geoprivacy, "locality_text": slide.locality_text, "country": slide.country}
    if slide.lat is None or slide.lon is None or slide.geoprivacy == "private":
        return c.PlaceRecord(**base)
    if slide.geoprivacy == "obscured":
        point, cell = obscure(slide.short_id, slide.lat, slide.lon)
        return c.PlaceRecord(**base, point=point, cell=cell)
    return c.PlaceRecord(**base, point=c.PointRecord(lat=slide.lat, lon=slide.lon), uncertainty_m=slide.uncertainty_m)


def iiif_identifier(storage_key: str) -> str:
    """A IIIF identifier is one path segment, so the slashes of a storage key are percent-encoded."""
    return quote(storage_key, safe="")


def media_record(asset: Asset, settings: Settings) -> c.MediaRecord:
    base = settings.public_base_url.rstrip("/")
    info = image = version = None
    if asset.media_kind == "pyramid" and asset.storage_key:
        info = f"{base}/iiif/{iiif_identifier(asset.storage_key)}/info.json"
        version = 3
    elif asset.media_kind == "image" and asset.storage_key:
        image = f"{base}/media/{asset.storage_key}"
    elif asset.media_kind == "remote_iiif":
        info = asset.remote_info_url
        version = asset.remote_iiif_version
    return c.MediaRecord(kind=asset.media_kind, iiif_info_url=info, image_url=image, iiif_version=version,
                         width_px=asset.width_px, height_px=asset.height_px)


def thumbnail_url(asset: Asset, settings: Settings, box: int = 320) -> str | None:
    media = media_record(asset, settings)
    if media.iiif_info_url:
        return media.iiif_info_url.removesuffix("/info.json") + f"/full/!{box},{box}/0/default.jpg"
    return media.image_url


def asset_record(asset: Asset, settings: Settings) -> c.AssetRecord:
    source = None
    if asset.source_url and asset.source_record_id and asset.source_retrieved_on and asset.source_sha256:
        source = c.SourceRecord(url=asset.source_url, record_id=asset.source_record_id,
                                retrieved_on=asset.source_retrieved_on, sha256=asset.source_sha256)
    plane = None
    if asset.stack is not None and asset.plane_index is not None and asset.plane_depth_um is not None:
        plane = c.PlaneRecord(stack=asset.stack, index=asset.plane_index, depth_um=asset.plane_depth_um)
    polarisation = None
    if asset.polarisation_state in ("ppl", "xpl"):
        polarisation = c.PolarisationRecord(state=asset.polarisation_state,
                                            angle_deg=asset.polarisation_angle_deg or 0.0)
    canon = licences.canonical(asset.licence_uri) or asset.licence_uri
    return c.AssetRecord(
        id=asset.id, family=asset.family, role=asset.role, sort_order=asset.sort_order, status=asset.status,
        media=media_record(asset, settings), pixel_size_um=asset.pixel_size_um, modality=asset.modality,
        plane=plane, polarisation=polarisation, caption=asset.caption,
        licence=c.LicenceRecord(uri=canon, short_name=licences.short_name(canon)),
        rights_holder=asset.rights_holder, creator=asset.creator, source=source,
        original_sha256=asset.source_sha256,
    )


def quality_checks(origin: str, assets) -> list[c.QualityCheckRecord]:
    """The slide checks (M9), each computed from what is stored: ``assets`` are the slide's asset rows (or anything
    with their ``family``, ``role``, ``licence_uri``, ``source_url``, ``pixel_size_um`` and ``modality``)."""
    assets = list(assets)
    micro = [a for a in assets if a.family == "micro"]
    macro = [a for a in assets if a.family == "macro"]
    # A composite fused from a focal stack (and its height map) is made from the stack's planes, whose licence and
    # source are recorded; it has a licence and no source of its own, so it is not a missing source.
    unsourced = [a for a in assets if not a.licence_uri
                 or (origin == "base" and not a.source_url and a.role not in DERIVED_ROLES)]
    unscaled = [a for a in micro if a.pixel_size_um is None]
    no_modality = [a for a in micro if not a.modality]
    checks = [
        c.QualityCheckRecord(code="licence_and_provenance", passed=not unsourced,
                             detail="every asset carries its licence and source" if not unsourced
                             else f"{len(unsourced)} asset(s) without licence or source"),
        c.QualityCheckRecord(code="scale", passed=bool(micro) and not unscaled,
                             detail="every micro image has a pixel size" if micro and not unscaled
                             else f"{len(unscaled)} micro image(s) without a pixel size" if micro
                             else "no micro image"),
        c.QualityCheckRecord(code="modality", passed=bool(micro) and not no_modality,
                             detail="every micro image states its imaging modality" if micro and not no_modality
                             else f"{len(no_modality)} micro image(s) without a modality" if micro
                             else "no micro image"),
        c.QualityCheckRecord(code="macro_and_micro", passed=bool(macro) and bool(micro),
                             detail=f"{len(macro)} macro and {len(micro)} micro asset(s)"),
    ]
    return checks


def quality_record(slide: Slide) -> c.QualityRecord:
    """The checks, and the badge the community keeps on the slide (U13); a slide it has not reached yet is judged by
    its checks alone."""
    checks = quality_checks(slide.origin, slide.assets)
    passed = all(ch.passed for ch in checks)
    badge = slide.badge if slide.badge in ("verified", "needs_id", "reference") else (
        "needs_id" if passed else "reference")
    if not passed:
        badge = "reference"
    return c.QualityRecord(badge=badge, checks=checks, community_node=slide.community_node,
                           community_rank=slide.community_rank)


def permalink(slide: Slide, settings: Settings) -> str:
    return f"{settings.public_base_url.rstrip('/')}/s/{slide.short_id}"


def anchor_record(slide: Slide) -> c.AnchorRecord:
    return c.AnchorRecord(kind=slide.anchor_kind, ref=slide.anchor_ref, name=slide.anchor_name,
                          rank=slide.anchor_rank, classification=slide.anchor_classification)


def format_record(slide: Slide) -> c.FormatRecord:
    return c.FormatRecord(code=slide.format_code, width_mm=slide.width_mm, height_mm=slide.height_mm,
                          assumed=bool(slide.format_assumed))


def slide_record(slide: Slide, settings: Settings, contributor: c.PersonRef | None = None) -> c.SlideRecord:
    link = permalink(slide, settings)
    coverslip = None
    if slide.coverslip_code != "none" and slide.coverslip_long_mm and slide.coverslip_short_mm:
        coverslip = c.CoverslipRecord(code=slide.coverslip_code, long_mm=slide.coverslip_long_mm,
                                      short_mm=slide.coverslip_short_mm)
    host = None
    if slide.host_ref and slide.host_name:
        host = c.AnchorRecord(kind="taxon", ref=slide.host_ref, name=slide.host_name, rank=slide.host_rank)
    return c.SlideRecord(
        id=slide.short_id,
        permalink=link,
        qr_payload=link.upper(),
        status=slide.status,
        origin=slide.origin,
        format=format_record(slide),
        coverslip=coverslip,
        label=c.LabelRecord(
            name=slide.anchor_name, catalogue_number=slide.catalogue_number, preparation=slide.preparation,
            stain=slide.stain, mountant=slide.mountant, label_note=slide.label_note,
            prepared_on=slide.prepared_on, preparer=slide.preparer, collected_on=slide.collected_on,
            collector=slide.collector, locality_text=slide.locality_text, type_status=slide.type_status,
        ),
        anchor=anchor_record(slide),
        host=host,
        part=slide.part,
        preservation=slide.preservation or "recent",
        place=place_record(slide),
        placement=c.PlacementRecord(node=slide.placement_node,
                                    overridden=bool(slide.placement_override_reason)),
        quality=quality_record(slide),
        assets=[asset_record(a, settings) for a in slide.assets],
        manifest_url=f"{settings.public_base_url.rstrip('/')}/api/slides/{slide.short_id}/manifest",
        contributor=contributor,
        created_at=slide.created_at,
        updated_at=slide.updated_at,
        published_at=slide.published_at,
    )


def slide_summary(slide: Slide, settings: Settings) -> c.SlideSummary:
    first_micro = next((a for a in slide.assets if a.family == "micro" and a.status == "ready"), None)
    first_any = first_micro or next((a for a in slide.assets if a.status == "ready"), None)
    return c.SlideSummary(
        id=slide.short_id, permalink=permalink(slide, settings), anchor=anchor_record(slide),
        format=format_record(slide),
        placement=c.PlacementRecord(node=slide.placement_node, overridden=bool(slide.placement_override_reason)),
        preparation=slide.preparation,
        thumbnail_url=thumbnail_url(first_any, settings) if first_any else None,
        origin=slide.origin,
        label=summary_label(slide),
    )


def summary_label(slide: Slide) -> c.SummaryLabel:
    return c.SummaryLabel(catalogue_number=slide.catalogue_number, collected_on=slide.collected_on,
                          locality_text=slide.locality_text, country=slide.country)
