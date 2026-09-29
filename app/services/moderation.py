"""Flags and the curators' hiding and restoring (U13, R-1305, R-1306; dossier 15, section 4).

Any signed-in account flags a slide, an identification or an annotation, with a category and a comment; the curators
list the open flags and resolve each with a comment. A curator hides an item with a reason of at least 10
characters: a hidden slide takes the ``hidden`` status (so every public listing, count, search, map, manifest and
tile leaves it) and its contributor sees the reason with the case; a hidden identification leaves the agreement and
is shown only to its author and the curators; a hidden annotation is not served. Only the curator who hid an item,
or an admin, restores it. Every hiding and restoring is kept.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

import httpx2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import roles
from app.contracts import catalog as c
from app.contracts.community import FlagIn
from app.db import short_id
from app.db.base import utcnow
from app.db.models import Annotation, Flag, Identification, ModerationAction, Slide, User
from app.services.community import CommunityRefused, recompute


@dataclass
class Target:
    kind: str
    id: str
    row: object
    slide: Slide
    #: The account that made the item (None for a base slide, or the source's identification).
    author_id: object | None


async def locate(db: AsyncSession, kind: str, target_id: str) -> Target:
    if kind == "slide":
        sid = short_id.normalise(target_id)
        slide = (await db.execute(select(Slide).where(Slide.short_id == sid))).scalar_one_or_none() if sid else None
        if slide is None or slide.status not in ("published", "hidden"):
            raise CommunityRefused(404, "no such slide")
        author = slide.contributor_id
        return Target(kind, slide.short_id, slide, slide, author)
    model = Identification if kind == "identification" else Annotation
    row = (await db.execute(select(model).where(model.public_id == target_id))).scalar_one_or_none()
    slide = await db.get(Slide, row.slide_id) if row is not None else None
    if row is None or slide is None or slide.status not in ("published", "hidden"):
        raise CommunityRefused(404, f"no such {kind}")
    author = row.user_id if kind == "identification" else row.author_id
    return Target(kind, target_id, row, slide, author)


def _hidden(target: Target) -> bool:
    if target.kind == "slide":
        return target.slide.status == "hidden"
    return bool(target.row.hidden)


async def _names(db: AsyncSession, ids: set) -> dict[str, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    users = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    return {str(u.id): u.display_name for u in users}


async def flag(db: AsyncSession, user: User, payload: FlagIn) -> c.FlagRecord:
    target = await locate(db, payload.target_kind, payload.target_id)
    if target.slide.status != "published" and not roles.allowed(user.role, "moderate"):
        raise CommunityRefused(404, f"no such {payload.target_kind}")
    row = Flag(public_id=secrets.token_hex(12), target_kind=payload.target_kind, target_id=target.id,
               slide_id=target.slide.id, user_id=user.id, category=payload.category,
               comment=payload.comment or None)
    db.add(row)
    await db.commit()
    return (await flag_records(db, [row]))[0]


async def flag_records(db: AsyncSession, rows: list[Flag]) -> list[c.FlagRecord]:
    names = await _names(db, {r.user_id for r in rows} | {r.resolved_by_id for r in rows})
    out = []
    for r in rows:
        slide = await db.get(Slide, r.slide_id)
        try:
            hidden = _hidden(await locate(db, r.target_kind, r.target_id))
        except CommunityRefused:
            hidden = False
        out.append(c.FlagRecord(
            id=r.public_id, target_kind=r.target_kind, target_id=r.target_id, slide_id=slide.short_id,
            slide_name=slide.anchor_name, category=r.category, comment=r.comment, by=names.get(str(r.user_id)),
            created_at=r.created_at, resolved_by=names.get(str(r.resolved_by_id)) if r.resolved_by_id else None,
            resolved_at=r.resolved_at, resolution=r.resolution, hidden=hidden))
    return out


async def flags(db: AsyncSession, status: str) -> list[c.FlagRecord]:
    query = select(Flag).order_by(Flag.created_at, Flag.id)
    if status == "open":
        query = query.where(Flag.resolved_at.is_(None))
    elif status == "resolved":
        query = query.where(Flag.resolved_at.is_not(None))
    return await flag_records(db, list((await db.execute(query)).scalars().all()))


async def resolve(db: AsyncSession, curator: User, public_id: str, resolution: str) -> c.FlagRecord:
    row = (await db.execute(select(Flag).where(Flag.public_id == public_id))).scalar_one_or_none()
    if row is None:
        raise CommunityRefused(404, "no such flag")
    if row.resolved_at is not None:
        raise CommunityRefused(409, "this flag is already resolved")
    row.resolved_by_id, row.resolved_at, row.resolution = curator.id, utcnow(), resolution
    await db.commit()
    return (await flag_records(db, [row]))[0]


async def _record(db: AsyncSession, actor: User, action: str, target: Target, reason: str) -> None:
    db.add(ModerationAction(actor_id=actor.id, action=action, target_kind=target.kind, target_id=target.id,
                            slide_id=target.slide.id, reason=reason))


async def hide(db: AsyncSession, client: httpx2.AsyncClient, curator: User, kind: str, target_id: str,
               reason: str) -> None:
    target = await locate(db, kind, target_id)
    if _hidden(target):
        raise CommunityRefused(409, f"this {kind} is already hidden")
    if kind == "slide":
        slide = target.slide
        slide.hidden_from, slide.status, slide.status_reason = slide.status, "hidden", reason[:300]
        slide.updated_at = utcnow()
    else:
        target.row.hidden = True
    await _record(db, curator, "hide", target, reason)
    await db.flush()
    if kind == "identification":
        await recompute(db, client, target.slide)
    await db.commit()


async def unhide(db: AsyncSession, client: httpx2.AsyncClient, actor: User, kind: str, target_id: str,
                 reason: str) -> None:
    target = await locate(db, kind, target_id)
    if not _hidden(target):
        raise CommunityRefused(409, f"this {kind} is not hidden")
    last = (await db.execute(select(ModerationAction).where(
        ModerationAction.target_kind == kind, ModerationAction.target_id == target.id,
        ModerationAction.action == "hide").order_by(ModerationAction.id.desc()))).scalars().first()
    if not roles.allowed(actor.role, "manage_accounts") and (last is None or last.actor_id != actor.id):
        raise CommunityRefused(403, "only the curator who hid it, or an admin, restores it")
    if kind == "slide":
        slide = target.slide
        slide.status, slide.hidden_from, slide.status_reason = slide.hidden_from or "published", None, None
        slide.updated_at = utcnow()
    else:
        target.row.hidden = False
    await _record(db, actor, "unhide", target, reason)
    await db.flush()
    if kind == "identification":
        await recompute(db, client, target.slide)
    await db.commit()


async def actions(db: AsyncSession, slide_raw: str | None = None) -> list[c.ModerationActionRecord]:
    query = select(ModerationAction).order_by(ModerationAction.id.desc())
    if slide_raw:
        sid = short_id.normalise(slide_raw)
        slide = (await db.execute(select(Slide).where(Slide.short_id == sid))).scalar_one_or_none() if sid else None
        if slide is None:
            return []
        query = query.where(ModerationAction.slide_id == slide.id)
    rows = list((await db.execute(query.limit(500))).scalars().all())
    names = await _names(db, {r.actor_id for r in rows})
    slides = {s.id: s.short_id for s in (await db.execute(
        select(Slide).where(Slide.id.in_({r.slide_id for r in rows})))).scalars().all()} if rows else {}
    return [c.ModerationActionRecord(action=r.action, target_kind=r.target_kind, target_id=r.target_id,
                                     slide_id=slides.get(r.slide_id, ""), reason=r.reason,
                                     by=names.get(str(r.actor_id)), created_at=r.created_at) for r in rows]
