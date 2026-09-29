"""The profile and its cabinet (U14, R-1401 to R-1403, R-1407; dossier 16, sections 3 and 4).

A profile is addressed by the account's handle and shows its role, when it joined and was last active (its newest
published slide or identification), its published slides in total and by collection, its verified slides, and its
identifications of others' slides by category (dossier 15). Nothing hidden counts, and the email is never read here.
The cabinet lists the account's published slides and its current visible identifications, each with whether it names
the slide's community anchor now. The export is the account's own, with each slide's exact place.
"""

from __future__ import annotations

import csv
import io
import json
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.community import store
from app.community.agreement import categories, community
from app.config import Settings
from app.contracts import catalog as c
from app.db.models import Annotation, Identification, Slide, User
from app.services import catalog, slides

CATEGORIES = ("leading", "improving", "supporting", "maverick")


class PersonNotFound(Exception):
    pass


async def by_handle(db: AsyncSession, handle: str) -> User:
    user = (await db.execute(select(User).where(User.handle == handle.lower()))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise PersonNotFound(handle)
    return user


def _own_published(user: User):
    return (Slide.status == "published", Slide.origin == "contribution", Slide.contributor_id == str(user.id))


async def _identified(db: AsyncSession, user: User) -> list[tuple[Identification, Slide]]:
    """The account's current, visible identifications of others' published slides."""
    rows = (await db.execute(
        select(Identification, Slide).join(Slide, Slide.id == Identification.slide_id)
        .where(Identification.user_id == user.id, Identification.current.is_(True), Identification.hidden.is_(False),
               Slide.status == "published", (Slide.contributor_id.is_(None)) | (Slide.contributor_id != str(user.id)))
        .order_by(Identification.created_at.desc(), Identification.id.desc()))).all()
    return [(i, s) for i, s in rows]


async def _category_of(db: AsyncSession, ident: Identification) -> str | None:
    def work(session):
        idents = store.idents_of(session.connection(), ident.slide_id)
        return categories(idents, community(idents)).get(ident.id)
    return await db.run_sync(work)


async def profile(db: AsyncSession, handle: str) -> c.ProfileRecord:
    user = await by_handle(db, handle)
    own = (await db.execute(select(Slide.placement_node, Slide.badge, Slide.published_at)
                            .where(*_own_published(user)))).all()
    by_collection = Counter(".".join(node.split(".")[:2]) for node, _, _ in own)
    identified = await _identified(db, user)
    counts = Counter()
    for ident, _ in identified:
        category = await _category_of(db, ident)
        if category:
            counts[category] += 1
    annotations = (await db.execute(select(func.count()).select_from(Annotation).join(
        Slide, Slide.id == Annotation.slide_id).where(Annotation.author_id == user.id, Annotation.hidden.is_(False),
                                                      Slide.status == "published"))).scalar_one()
    moments = [p for _, _, p in own if p] + [i.created_at for i, _ in identified]
    return c.ProfileRecord(
        handle=user.handle, name=user.display_name, role=user.role, joined=user.created_at,
        last_active=max(moments) if moments else None, slides=len(own),
        verified=sum(1 for _, badge, _ in own if badge == "verified"),
        by_collection=dict(sorted(by_collection.items())), identifications=len(identified),
        categories={k: counts.get(k, 0) for k in CATEGORIES}, annotations=int(annotations))


async def cabinet_slides(db: AsyncSession, handle: str, settings: Settings, collection: str | None, offset: int,
                         limit: int) -> c.SlidePage:
    user = await by_handle(db, handle)
    conditions = list(_own_published(user))
    if collection:
        conditions.append((Slide.placement_node == collection) | Slide.placement_node.startswith(collection + "."))
    total = (await db.execute(select(func.count()).select_from(Slide).where(*conditions))).scalar_one()
    ids = (await db.execute(select(Slide.id).where(*conditions).order_by(Slide.placement_node, Slide.published_at,
                                                                          Slide.id).offset(offset).limit(limit)))
    ids = list(ids.scalars().all())
    rows = await slides.slides_by_ids(db, ids)
    order = {sid: i for i, sid in enumerate(ids)}
    rows.sort(key=lambda s: order[s.id])
    return c.SlidePage(items=[catalog.slide_summary(s, settings) for s in rows], total=int(total), offset=offset,
                       limit=limit)


async def cabinet_identifications(db: AsyncSession, handle: str, settings: Settings, offset: int,
                                  limit: int) -> list[c.PersonIdentificationRecord]:
    user = await by_handle(db, handle)
    chosen = (await _identified(db, user))[offset:offset + limit]
    loaded = {s.id: s for s in await slides.slides_by_ids(db, [s.id for _, s in chosen])}
    out = []
    for ident, slide in chosen:
        node = json.loads(ident.lineage_json)[-1]
        out.append(c.PersonIdentificationRecord(
            id=ident.public_id, slide=catalog.slide_summary(loaded[slide.id], settings),
            anchor=c.AnchorRecord(kind=ident.anchor_kind, ref=ident.anchor_ref, name=ident.anchor_name,
                                  rank=ident.anchor_rank, classification=ident.anchor_classification),
            category=await _category_of(db, ident), community=node == slide.community_node,
            created_at=ident.created_at))
    return out


EXPORT_COLUMNS = ("id", "status", "badge", "catalogue_number", "anchor_kind", "anchor_ref", "anchor_name",
                  "anchor_rank", "community_node", "placement_node", "format", "preparation", "stain", "mountant",
                  "prepared_on", "preparer", "collected_on", "collector", "locality_text", "country", "latitude",
                  "longitude", "uncertainty_m", "geoprivacy", "permalink", "created_at", "published_at")


async def export(db: AsyncSession, user: User, settings: Settings) -> str:
    """The account's own slides as CSV, any status, with each exact place (only its owner reads this)."""
    rows = (await db.execute(select(Slide).where(Slide.origin == "contribution", Slide.contributor_id == str(user.id))
                             .order_by(Slide.created_at, Slide.id))).scalars().all()
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(EXPORT_COLUMNS)
    for s in rows:
        writer.writerow([s.short_id, s.status, s.badge or "", s.catalogue_number or "", s.anchor_kind, s.anchor_ref,
                         s.anchor_name, s.anchor_rank or "", s.community_node or "", s.placement_node, s.format_code,
                         s.preparation, s.stain or "", s.mountant or "", s.prepared_on or "", s.preparer or "",
                         s.collected_on or "", s.collector or "", s.locality_text or "", s.country or "",
                         "" if s.lat is None else s.lat, "" if s.lon is None else s.lon,
                         "" if s.uncertainty_m is None else s.uncertainty_m, s.geoprivacy,
                         catalog.permalink(s, settings), s.created_at.isoformat(),
                         s.published_at.isoformat() if s.published_at else ""])
    return out.getvalue()
