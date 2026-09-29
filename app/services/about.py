"""The About place's numbers and credits (U15, R-1501, R-1502, R-1507; dossier 17).

Everything counted comes from the database when the page is read: published slides in total, by realm and collection
and by origin, whole-slide scans, images, countries, contributors, the community's identifications, and the images by
source and by licence. An image is a source image of a published slide: a focal plane counts, a composite fused from
a stack does not. A source is known by the host its files come from (``app/about/credits.json``); a contribution's
images are its contributor's; a host no source claims is "other", which the tests forbid for the base collection.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import catalog as c
from app.contracts import licences
from app.db.models import Asset, Identification, Slide
from app.services.catalog import DERIVED_ROLES
from app.services.explore import WHOLE_SLIDE_ROLES

CREDITS = Path(__file__).resolve().parents[1] / "about" / "credits.json"
CONTRIBUTION = "contribution"
OTHER = "other"
#: The licence families the policy accepts, by origin (``app/contracts/licences.py``).
POLICY = {"base": ["cc0", "pdm", "nkc", "by", "by-sa"],
          "contribution": ["cc0", "pdm", "nkc", "by", "by-sa", "by-nc", "by-nc-sa"]}
_FAMILY = re.compile(r"/licenses/(?P<family>[a-z-]+)/")


@lru_cache
def credits() -> dict:
    return json.loads(CREDITS.read_text(encoding="utf-8"))


def source_of(url: str | None, origin: str) -> str:
    """The id of the source an image came from: a contribution's is its contributor's."""
    if origin == CONTRIBUTION:
        return CONTRIBUTION
    host = urlparse(url or "").netloc.lower()
    for source in credits()["sources"]:
        if host in source["hosts"]:
            return source["id"]
    return OTHER


def family(uri: str) -> str:
    """cc0, pdm, nkc, or the Creative Commons family of a licence URI (by, by-sa, by-nc, ...)."""
    canon = licences.canonical(uri) or uri
    if canon == licences.CC0:
        return "cc0"
    if canon == licences.PDM:
        return "pdm"
    if canon == licences.NKC:
        return "nkc"
    m = _FAMILY.search(canon)
    return m["family"] if m else "other"


def _credit(item: dict) -> c.CreditRecord:
    return c.CreditRecord(id=item["id"], name=item["name"], url=item["url"], licence=item.get("licence"),
                          citation=item.get("citation"), doi=item.get("doi"), terms=item.get("terms"))


async def about(db: AsyncSession) -> c.AboutRecord:
    published = Slide.status == "published"
    nodes = (await db.execute(select(Slide.placement_node, Slide.origin, func.count()).where(published)
                              .group_by(Slide.placement_node, Slide.origin))).all()
    realms: dict[str, Counter] = defaultdict(Counter)
    by_origin: Counter = Counter()
    for node, origin, n in nodes:
        parts = node.split(".")
        realms[parts[0]][".".join(parts[:2])] += n
        by_origin[origin] += n
    whole = select(Asset.slide_id).where(Asset.family == "micro", Asset.role.in_(WHOLE_SLIDE_ROLES)).distinct()
    wsi = (await db.execute(select(func.count()).select_from(Slide).where(published, Slide.id.in_(whole))))\
        .scalar_one()
    countries = (await db.execute(select(func.count(func.distinct(Slide.country)))
                                  .where(published, Slide.country.is_not(None)))).scalar_one()
    contributors = (await db.execute(select(func.count(func.distinct(Slide.contributor_id)))
                                     .where(published, Slide.origin == CONTRIBUTION))).scalar_one()
    identifications = (await db.execute(
        select(func.count()).select_from(Identification).join(Slide, Slide.id == Identification.slide_id)
        .where(published, Identification.current.is_(True), Identification.hidden.is_(False),
               Identification.user_id.is_not(None),
               # Both hold the account's UUID as text: an identification of one's own slide is not the community's.
               (Slide.contributor_id.is_(None)) | (Slide.contributor_id != Identification.user_id))
    )).scalar_one()

    images = (await db.execute(
        select(Asset.slide_id, Asset.source_url, Asset.licence_uri, Slide.origin)
        .join(Slide, Slide.id == Asset.slide_id)
        .where(published, Asset.status == "ready", Asset.role.not_in(DERIVED_ROLES)))).all()
    per_source: dict[str, dict] = defaultdict(lambda: {"slides": set(), "images": 0, "licences": Counter()})
    per_licence: Counter = Counter()
    for slide_id, url, licence, origin in images:
        entry = per_source[source_of(url, origin)]
        entry["slides"].add(slide_id)
        entry["images"] += 1
        uri = licences.canonical(licence or "") or (licence or "")
        entry["licences"][uri] += 1
        per_licence[uri] += 1

    known = {s["id"]: s for s in credits()["sources"]}
    order = [s["id"] for s in credits()["sources"]] + [CONTRIBUTION, OTHER]
    sources = [c.SourceCount(id=sid, name=known.get(sid, {}).get("name"), url=known.get(sid, {}).get("url"),
                             terms=known.get(sid, {}).get("terms"), slides=len(per_source[sid]["slides"]),
                             images=per_source[sid]["images"],
                             licences=dict(per_source[sid]["licences"].most_common()))
               for sid in order if sid in per_source]
    licence_rows = [c.LicenceCount(uri=uri, short=licences.short_name(uri), family=family(uri), images=n)
                    for uri, n in per_licence.most_common()]
    return c.AboutRecord(
        read_at=datetime.now(UTC).replace(tzinfo=None),
        numbers=c.AboutNumbers(
            slides=sum(by_origin.values()), by_origin=dict(sorted(by_origin.items())), wsi=int(wsi),
            images=len(images), countries=int(countries), contributors=int(contributors),
            identifications=int(identifications),
            realms=[c.RealmCount(id=realm, slides=sum(cols.values()), collections=dict(sorted(cols.items())))
                    for realm, cols in sorted(realms.items())]),
        sources=sources, licences=licence_rows, policy=POLICY,
        vocabularies=[_credit(v) for v in credits()["vocabularies"]],
        map=[_credit(v) for v in credits()["map"]],
        software=[_credit(v) for v in credits()["software"]],
        fonts=[_credit(v) for v in credits()["fonts"]])
