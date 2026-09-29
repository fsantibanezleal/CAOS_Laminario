"""Identifications and votes on a published slide, through the API (U13, R-1301 to R-1304).

An identification's anchor is resolved as a submission's is (the GBIF backbone for a taxon, cached; the vocabularies
for the other kinds) and stored with its lineage, the slide's anchor of the time and, when it names an ancestor of
that anchor, whether it disagrees with the finer one (R-1302). Every change recomputes the community: when the node
changes, the votes are cleared and the slide follows the community anchor when it is one Laminario can name (R-1303),
keeping its drawer when the drawer still accepts it; the badge is computed again (R-1304). The work is
``app/community/store.refresh``'s, on the session's connection.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass

import httpx2
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.collections import taxa, vocab
from app.community import store
from app.community.agreement import Community, Ident, categories, community
from app.community.lineage import kind_of, taxon_lineage, term_lineage
from app.contracts.ingest import Anchor
from app.db import short_id
from app.db.base import utcnow
from app.db.models import Identification, Slide, SlideVote, User


class CommunityRefused(Exception):
    def __init__(self, status: int, message: str, code: str = "", params: dict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.params = params or {}


@dataclass(frozen=True)
class Resolved:
    kind: str
    ref: str
    name: str
    rank: str | None
    classification: str | None
    lineage: tuple[str, ...]


async def resolve(db: AsyncSession, client: httpx2.AsyncClient, anchor: Anchor) -> Resolved:
    """An identification's anchor, canonical and with its lineage; refused with the rule's code when it does not
    resolve."""
    if anchor.kind == "taxon":
        if not anchor.ref.isdigit():
            raise CommunityRefused(422, "a taxon is referenced by its GBIF usage key", "taxon_key_expected")
        found = await taxa.lineage(db, client, int(anchor.ref))
        if found is None:
            raise CommunityRefused(422, f"{anchor.ref} is not a taxon of the GBIF backbone", "taxon_unknown",
                                   {"ref": anchor.ref})
        return Resolved("taxon", anchor.ref, found.name, found.rank, None, taxon_lineage(found))
    term = vocab.resolve_term(anchor.kind, anchor.ref, anchor.classification, field="anchor")
    if isinstance(term, vocab.Problem):
        raise CommunityRefused(422, term.message, term.code, term.params)
    return Resolved(anchor.kind, term.ref, anchor.name, term.rank, term.classification,
                    term_lineage(anchor.kind, term))


async def slide_lineage(db: AsyncSession, client: httpx2.AsyncClient, slide: Slide) -> tuple[str, ...] | None:
    anchor = Anchor(kind=slide.anchor_kind, ref=slide.anchor_ref, name=slide.anchor_name, rank=slide.anchor_rank,
                    classification=slide.anchor_classification)
    try:
        return (await resolve(db, client, anchor)).lineage
    except CommunityRefused:
        return None


async def published(db: AsyncSession, raw_id: str) -> Slide:
    sid = short_id.normalise(raw_id)
    slide = (await db.execute(select(Slide).options(selectinload(Slide.assets))
                              .where(Slide.short_id == sid, Slide.status == "published"))).scalar_one_or_none() \
        if sid else None
    if slide is None:
        raise CommunityRefused(404, "no such published slide")
    return slide


async def rows_of(db: AsyncSession, slide_id: int) -> list[Identification]:
    return list((await db.execute(select(Identification).where(Identification.slide_id == slide_id)
                                  .order_by(Identification.id))).scalars().all())


def as_ident(row: Identification) -> Ident:
    return Ident(order=row.id, account=str(row.user_id) if row.user_id else "source",
                 lineage=tuple(json.loads(row.lineage_json)), current=row.current, hidden=row.hidden,
                 disagreement=row.disagreement,
                 previous=tuple(json.loads(row.previous_lineage_json)) if row.previous_lineage_json else None)


async def recompute(db: AsyncSession, client: httpx2.AsyncClient, slide: Slide) -> Community:
    """The community again, after any change. A community taxon above the ones named may not be cached yet: it is
    fetched once, so the synchronous refresh (which never reads the network) can make the slide follow it."""
    rows = await rows_of(db, slide.id)
    result = community([as_ident(r) for r in rows])
    if result.node and kind_of(result.node) == "taxon":
        try:
            await taxa.lineage(db, client, int(result.node.split(":", 1)[1]))
        except taxa.TaxonServiceUnavailable:
            pass  # the slide keeps its anchor until the next change reaches GBIF
    await db.flush()
    result = await db.run_sync(lambda session: store.refresh(session.connection(), slide.id))
    await db.refresh(slide)
    return result


async def identify(db: AsyncSession, client: httpx2.AsyncClient, user: User, raw_id: str, anchor: Anchor,
                   body: str | None, disagreement: bool | None) -> Identification:
    slide = await published(db, raw_id)
    resolved = await resolve(db, client, anchor)
    previous = await slide_lineage(db, client, slide)
    node = resolved.lineage[-1]
    ancestor = previous is not None and node in previous[:-1]
    if ancestor and disagreement is None:
        raise CommunityRefused(422, "an identification of an ancestor of the slide's anchor says whether it disagrees "
                               "with the finer anchor", "disagreement_unstated", {"anchor": slide.anchor_name})
    await db.execute(update(Identification).where(Identification.slide_id == slide.id,
                                                  Identification.user_id == user.id).values(current=False))
    row = Identification(
        public_id=secrets.token_hex(12), slide_id=slide.id, user_id=user.id, anchor_kind=resolved.kind,
        anchor_ref=resolved.ref, anchor_name=resolved.name, anchor_rank=resolved.rank,
        anchor_classification=resolved.classification, lineage_json=json.dumps(list(resolved.lineage)),
        previous_lineage_json=json.dumps(list(previous)) if previous else None,
        disagreement=bool(disagreement) if ancestor else None, body=(body or "").strip() or None, current=True)
    db.add(row)
    await db.flush()
    await recompute(db, client, slide)
    await db.commit()
    return row


async def own(db: AsyncSession, user: User, public_id: str) -> tuple[Identification, Slide]:
    row = (await db.execute(select(Identification).where(Identification.public_id == public_id))).scalar_one_or_none()
    if row is None or row.user_id != user.id:
        raise CommunityRefused(404, "no such identification of yours")
    slide = await db.get(Slide, row.slide_id)
    if slide is None or slide.status != "published":
        raise CommunityRefused(404, "no such published slide")
    return row, slide


async def withdraw(db: AsyncSession, client: httpx2.AsyncClient, user: User, public_id: str) -> None:
    row, slide = await own(db, user, public_id)
    row.current = False
    row.updated_at = utcnow()
    await recompute(db, client, slide)
    await db.commit()


async def restore(db: AsyncSession, client: httpx2.AsyncClient, user: User, public_id: str) -> None:
    row, slide = await own(db, user, public_id)
    if row.hidden:
        raise CommunityRefused(409, "a hidden identification is restored by a curator")
    await db.execute(update(Identification).where(Identification.slide_id == slide.id,
                                                  Identification.user_id == user.id).values(current=False))
    row.current = True
    row.updated_at = utcnow()
    await recompute(db, client, slide)
    await db.commit()


async def vote(db: AsyncSession, client: httpx2.AsyncClient, user: User, raw_id: str,
               as_good_as_it_can_be: bool | None) -> None:
    """An identifier's answer to "can the community anchor still be improved?"; None takes the vote back."""
    slide = await published(db, raw_id)
    await db.execute(delete(SlideVote).where(SlideVote.slide_id == slide.id, SlideVote.user_id == user.id))
    if as_good_as_it_can_be is not None:
        db.add(SlideVote(slide_id=slide.id, user_id=user.id, as_good_as_it_can_be=as_good_as_it_can_be))
    await db.flush()
    await db.run_sync(lambda session: store.refresh(session.connection(), slide.id))
    await db.commit()


@dataclass
class Listing:
    slide: Slide
    result: Community
    rows: list[Identification]
    names: dict[str, str]
    categories: dict[int, str]
    votes: tuple[int, int]


async def listing(db: AsyncSession, raw_id: str, viewer: User | None, may_moderate: bool) -> Listing:
    """A slide's identifications as a viewer may see them: hidden ones only to their author and the curators."""
    slide = await published(db, raw_id)
    rows = await rows_of(db, slide.id)
    result = community([as_ident(r) for r in rows])
    ids = {r.user_id for r in rows if r.user_id}
    users = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all() if ids else []
    names = {str(u.id): u.display_name for u in users}
    visible = [r for r in rows if not r.hidden or may_moderate or (viewer is not None and r.user_id == viewer.id)]
    votes = await db.run_sync(lambda session: store.votes(session.connection(), slide.id))
    return Listing(slide, result, visible, names, categories([as_ident(r) for r in rows], result), votes)
