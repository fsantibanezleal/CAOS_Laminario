"""Store a validated slide case, and read slides back.

``create_slide`` maps a validated submission to rows: one ``slide`` and one ``asset`` per asset, all
pending until processing makes them ready (the worker, U4). Short ids are drawn until one is free.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contracts import licences
from app.contracts.ingest import SlideCaseSubmission, coverslip_size_mm, slide_size_mm
from app.db import short_id
from app.db.models import Asset, Slide

MAX_ID_ATTEMPTS = 8


def _media_kind(asset) -> str:
    if asset.remote_iiif is not None:
        return "remote_iiif"
    return "pyramid" if asset.family == "micro" else "image"


def slide_from_submission(sub: SlideCaseSubmission, *, new_id: str, contributor_id: str | None = None) -> Slide:
    """The rows for a validated submission (not yet added to a session)."""
    width, height = slide_size_mm(sub.slide)
    cover = coverslip_size_mm(sub.slide)
    sp = sub.specimen
    slide = Slide(
        short_id=new_id,
        status="draft",
        origin=sub.origin,
        format_code=sub.slide.format,
        width_mm=width,
        height_mm=height,
        coverslip_code=sub.slide.coverslip,
        coverslip_long_mm=cover[0] if cover else None,
        coverslip_short_mm=cover[1] if cover else None,
        preparation=sub.slide.preparation,
        stain=sub.slide.stain,
        mountant=sub.slide.mountant,
        catalogue_number=sub.slide.catalogue_number,
        label_note=sub.slide.label_note,
        prepared_on=sub.slide.prepared_on,
        preparer=sub.slide.preparer,
        anchor_kind=sp.anchor.kind,
        anchor_ref=sp.anchor.ref,
        anchor_name=sp.anchor.name,
        anchor_rank=sp.anchor.rank,
        host_ref=sp.host.ref if sp.host else None,
        host_name=sp.host.name if sp.host else None,
        host_rank=sp.host.rank if sp.host else None,
        type_status=sp.type_status,
        collected_on=sp.collected_on,
        collector=sp.collector,
        locality_text=sp.locality_text,
        lat=sp.coordinates.lat if sp.coordinates else None,
        lon=sp.coordinates.lon if sp.coordinates else None,
        uncertainty_m=sp.coordinates.uncertainty_m if sp.coordinates else None,
        geoprivacy=sp.geoprivacy,
        placement_node=sub.placement.node,
        placement_override_reason=sub.placement.override_reason,
        contributor_id=contributor_id,
    )
    for order, a in enumerate(sub.assets):
        slide.assets.append(Asset(
            family=a.family,
            role=a.role,
            sort_order=order,
            media_kind=_media_kind(a),
            status="pending",
            pixel_size_um=a.pixel_size_um,
            modality=a.modality,
            stack=a.plane.stack if a.plane else None,
            plane_index=a.plane.index if a.plane else None,
            plane_depth_um=a.plane.depth_um if a.plane else None,
            polarisation_state=a.polarisation.state if a.polarisation else None,
            polarisation_angle_deg=a.polarisation.angle_deg if a.polarisation else None,
            caption=a.caption,
            licence_uri=licences.canonical(a.licence) or a.licence,
            rights_holder=a.rights_holder,
            creator=a.creator,
            source_url=str(a.source.url) if a.source else None,
            source_record_id=a.source.record_id if a.source else None,
            source_retrieved_on=a.source.retrieved_on if a.source else None,
            source_sha256=a.source.sha256 if a.source else None,
            remote_info_url=str(a.remote_iiif) if a.remote_iiif else None,
        ))
    return slide


async def create_slide(session: AsyncSession, sub: SlideCaseSubmission, *, contributor_id: str | None = None,
                       generate: Callable[[], str] = short_id.generate) -> Slide:
    """Store a validated submission as a draft slide with pending assets; retry on a short-id collision."""
    for _ in range(MAX_ID_ATTEMPTS):
        slide = slide_from_submission(sub, new_id=generate(), contributor_id=contributor_id)
        session.add(slide)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            continue
        await session.commit()
        return slide
    raise RuntimeError(f"no free short id after {MAX_ID_ATTEMPTS} attempts")


def _with_assets():
    return select(Slide).options(selectinload(Slide.assets))


async def get_slide(session: AsyncSession, raw_id: str, *, published_only: bool = True) -> Slide | None:
    """A slide by its short id as typed or scanned (case and look-alike letters forgiven)."""
    sid = short_id.normalise(raw_id)
    if sid is None:
        return None
    query = _with_assets().where(Slide.short_id == sid)
    if published_only:
        query = query.where(Slide.status == "published")
    return (await session.execute(query)).scalar_one_or_none()


async def list_slides(session: AsyncSession, *, node: str | None = None, kind: str | None = None,
                      offset: int = 0, limit: int = 48) -> tuple[list[Slide], int]:
    """Published slides, optionally under a collection node (itself or any descendant) or of an anchor kind."""
    conditions = [Slide.status == "published"]
    if node:
        conditions.append((Slide.placement_node == node) | Slide.placement_node.startswith(node + "."))
    if kind:
        conditions.append(Slide.anchor_kind == kind)
    total = (await session.execute(select(func.count()).select_from(Slide).where(*conditions))).scalar_one()
    rows = (await session.execute(
        _with_assets().where(*conditions).order_by(Slide.published_at.desc(), Slide.id.desc())
        .offset(offset).limit(limit)
    )).scalars().all()
    return list(rows), int(total)
