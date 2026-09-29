"""Explore: filters over published slides, the counts beside each filter value, and the map's aggregates.

A filter narrows by the slide's own fields (anchor kind, preparation, preservation, country, origin) or by its assets
(modality, whole-slide, licence family). Text goes through the FTS5 index (``app/services/search.py``). The counts
next to a facet's values are computed with every other active filter applied but not the facet's own, so choosing a
second value of a facet shows how many it would add (the usual faceted-search behaviour). The map returns countries
with their slide counts and the points of slides with coordinates, after geoprivacy: an obscured slide appears at its
public point in its 0.2 degree cell, a private one not at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from sqlalchemy import case, exists, func, literal_column, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Asset, Slide
from app.services import search
from app.services.catalog import obscure

WHOLE_SLIDE_ROLES = ("pyramid", "z_plane")
FACETS = ("kind", "preparation", "modality", "preservation", "country", "licence", "wsi", "origin")
SORTS = ("newest", "name", "relevance")

#: A licence URI's family, for the licence facet (the URIs are canonical: app/contracts/licences.py).
LICENCE_FAMILY = case(
    (Asset.licence_uri.contains("/publicdomain/") | Asset.licence_uri.contains("/NKC/"), "public-domain"),
    (Asset.licence_uri.contains("/by-nc-sa/"), "by-nc-sa"),
    (Asset.licence_uri.contains("/by-nc/"), "by-nc"),
    (Asset.licence_uri.contains("/by-sa/"), "by-sa"),
    (Asset.licence_uri.contains("/by/"), "by"),
    else_="other",
)


@dataclass(frozen=True)
class Filters:
    node: str | None = None
    kind: tuple[str, ...] = ()
    preparation: tuple[str, ...] = ()
    modality: tuple[str, ...] = ()
    preservation: tuple[str, ...] = ()
    country: tuple[str, ...] = ()
    licence: tuple[str, ...] = ()
    wsi: bool | None = None
    origin: tuple[str, ...] = ()
    q: str | None = None
    skip: set[str] = field(default_factory=set)

    def without(self, facet: str) -> Filters:
        return replace(self, skip={facet})


def _match(expression: str):
    """The FTS5 condition with its expression bound on the clause itself, so it holds inside any subquery."""
    return text("slide_search MATCH :fts").bindparams(fts=expression)


def _asset_exists(*conditions):
    return exists(select(Asset.id).where(Asset.slide_id == Slide.id, *conditions))


def conditions(f: Filters) -> list:
    out = [Slide.status == "published"]
    if f.node:
        out.append((Slide.placement_node == f.node) | Slide.placement_node.startswith(f.node + "."))
    if f.kind and "kind" not in f.skip:
        out.append(Slide.anchor_kind.in_(f.kind))
    if f.preparation and "preparation" not in f.skip:
        out.append(Slide.preparation.in_(f.preparation))
    if f.preservation and "preservation" not in f.skip:
        out.append(Slide.preservation.in_(f.preservation))
    if f.country and "country" not in f.skip:
        out.append(Slide.country.in_(f.country))
    if f.origin and "origin" not in f.skip:
        out.append(Slide.origin.in_(f.origin))
    if f.modality and "modality" not in f.skip:
        out.append(_asset_exists(Asset.modality.in_(f.modality)))
    if f.licence and "licence" not in f.skip:
        out.append(_asset_exists(LICENCE_FAMILY.in_(f.licence)))
    if f.wsi is not None and "wsi" not in f.skip:
        whole = _asset_exists(Asset.family == "micro", Asset.role.in_(WHOLE_SLIDE_ROLES))
        out.append(whole if f.wsi else ~whole)
    expression = search.fts_query(f.q) if f.q else None
    if expression:
        out.append(Slide.id.in_(select(literal_column("rowid")).select_from(text("slide_search"))
                                .where(_match(expression))))
    return out


async def slide_ids(db: AsyncSession, f: Filters, sort: str, offset: int, limit: int) -> tuple[list[int], int]:
    where = conditions(f)
    total = (await db.execute(select(func.count()).select_from(Slide).where(*where))).scalar_one()
    query = select(Slide.id).where(*where)
    expression = search.fts_query(f.q) if f.q else None
    if sort == "relevance" and expression:
        rank = (select(literal_column("rowid").label("rid"), literal_column("bm25(slide_search)").label("score"))
                .select_from(text("slide_search")).where(_match(expression)).subquery())
        query = query.join(rank, rank.c.rid == Slide.id).order_by(rank.c.score, Slide.id)
    elif sort == "name":
        query = query.order_by(func.lower(Slide.anchor_name), Slide.id)
    else:
        query = query.order_by(Slide.published_at.desc(), Slide.id.desc())
    rows = (await db.execute(query.offset(offset).limit(limit))).scalars().all()
    return list(rows), int(total)


async def facet_counts(db: AsyncSession, f: Filters) -> dict[str, dict[str, int]]:
    """For every facet, its values and how many slides each would match, the facet's own filter left out."""
    out: dict[str, dict[str, int]] = {}
    for facet in FACETS:
        where = conditions(f.without(facet))
        if facet in ("kind", "preparation", "preservation", "country", "origin"):
            column = {"kind": Slide.anchor_kind, "preparation": Slide.preparation, "preservation": Slide.preservation,
                      "country": Slide.country, "origin": Slide.origin}[facet]
            rows = (await db.execute(select(column, func.count()).where(*where, column.is_not(None))
                                     .group_by(column))).all()
        elif facet in ("modality", "licence"):
            value = Asset.modality if facet == "modality" else LICENCE_FAMILY
            rows = (await db.execute(
                select(value, func.count(func.distinct(Slide.id))).select_from(Slide)
                .join(Asset, Asset.slide_id == Slide.id).where(*where, value.is_not(None)).group_by(value))).all()
        else:  # wsi
            whole = _asset_exists(Asset.family == "micro", Asset.role.in_(WHOLE_SLIDE_ROLES))
            rows = (await db.execute(select(case((whole, "yes"), else_="no"), func.count()).where(*where)
                                     .group_by(case((whole, "yes"), else_="no")))).all()
        out[facet] = {str(k): int(v) for k, v in rows if k is not None}
    return out


@dataclass
class MapPoint:
    id: str
    lat: float
    lon: float
    obscured: bool
    cell: tuple[float, float, float, float] | None = None


async def map_data(db: AsyncSession, f: Filters, limit: int = 5000) -> tuple[dict[str, int], list[MapPoint], int]:
    """Countries with their slide counts, the points of slides with coordinates (after geoprivacy), and how many
    slides the filters match in all."""
    where = conditions(f)
    countries = dict((await db.execute(select(Slide.country, func.count()).where(*where, Slide.country.is_not(None))
                                       .group_by(Slide.country))).all())
    total = (await db.execute(select(func.count()).select_from(Slide).where(*where))).scalar_one()
    rows = (await db.execute(
        select(Slide.short_id, Slide.lat, Slide.lon, Slide.geoprivacy)
        .where(*where, Slide.lat.is_not(None), Slide.lon.is_not(None), Slide.geoprivacy != "private")
        .order_by(Slide.id).limit(limit))).all()
    points = []
    for short_id, lat, lon, privacy in rows:
        if privacy == "obscured":
            point, cell = obscure(short_id, lat, lon)
            bounds = (cell.south, cell.west, cell.north, cell.east)
            points.append(MapPoint(short_id, point.lat, point.lon, True, bounds))
        else:
            points.append(MapPoint(short_id, lat, lon, False))
    return {str(k): int(v) for k, v in countries.items()}, points, int(total)


def as_tuple(values: list[str] | None) -> tuple[str, ...]:
    return tuple(v for v in (values or []) if v)
