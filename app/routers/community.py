"""The community: identifications, votes, the Identify queue, flags and moderation (U13).

| Route | Who |
|---|---|
| `GET /api/slides/{id}/identifications` | anyone, on a published slide (hidden ones: their author and the curators) |
| `POST /api/slides/{id}/identifications` | the ``identify`` capability (identifier and above) |
| `POST /api/identifications/{id}/withdraw`, `.../restore` | the identification's account |
| `PUT /api/slides/{id}/vote` | the ``identify`` capability |
| `GET /api/identify` | anyone: published slides by badge, collection and kind, oldest first |
| `POST /api/flags` | any signed-in account |
| `GET /api/flags`, `POST /api/flags/{id}/resolve` | the ``moderate`` capability (curator and above) |
| `POST /api/moderation/{kind}/{id}/hide`, `.../unhide` | ``moderate``; restoring: the curator who hid, or an admin |
| `GET /api/moderation/actions`, `GET /api/moderation/hidden` | the ``moderate`` capability |

Built per application, like the accounts routes, because the signed-in account comes from the settings' accounts.
"""
# No ``from __future__ import annotations``: the dependency aliases are defined inside ``routers`` and FastAPI must
# see them as objects.
import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import roles
from app.accounts.users import Accounts
from app.community.agreement import CUTOFF
from app.contracts import catalog as c
from app.contracts.community import FlagIn, IdentificationIn, ReasonIn, ResolveIn, TargetKind, VoteIn
from app.db.models import Annotation, Identification, Slide, SlideVote, User
from app.db.session import session
from app.routers.accounts import requirement
from app.services import catalog, community, moderation, slides


def refused(exc: community.CommunityRefused) -> HTTPException:
    if exc.code:
        return HTTPException(status_code=exc.status, detail={"code": exc.code, "reason": str(exc),
                                                              "params": exc.params})
    return HTTPException(status_code=exc.status, detail=str(exc))


def identification_record(row: Identification, names: dict[str, str], viewer: User | None,
                          category: str | None) -> c.IdentificationRecord:
    lineage = json.loads(row.lineage_json)
    return c.IdentificationRecord(
        id=row.public_id, node=lineage[-1],
        anchor=c.AnchorRecord(kind=row.anchor_kind, ref=row.anchor_ref, name=row.anchor_name, rank=row.anchor_rank,
                              classification=row.anchor_classification),
        by=names.get(str(row.user_id)) if row.user_id else None, source=row.user_id is None,
        mine=viewer is not None and row.user_id == viewer.id, body=row.body, disagreement=row.disagreement,
        current=row.current, hidden=row.hidden, category=category if row.current and not row.hidden else None,
        created_at=row.created_at)


def routers(accounts: Accounts) -> list[APIRouter]:
    api = APIRouter(prefix="/api", tags=["community"])
    Db = Annotated[AsyncSession, Depends(session)]
    Identifier = Annotated[User, Depends(requirement(accounts, "identify"))]
    Curator = Annotated[User, Depends(requirement(accounts, "moderate"))]
    Member = Annotated[User, Depends(accounts.current)]
    Reader = Annotated[User | None, Depends(accounts.optional)]

    @api.get("/slides/{slide_id}/identifications", response_model=c.IdentificationList)
    async def list_identifications(slide_id: str, db: Db, reader: Reader) -> c.IdentificationList:
        may_moderate = reader is not None and roles.allowed(reader.role, "moderate")
        try:
            found = await community.listing(db, slide_id, reader, may_moderate)
        except community.CommunityRefused as exc:
            raise refused(exc) from exc
        slide, result = found.slide, found.result
        score = next((s.score for s in result.scores if s.node == result.node), None)
        my_vote = None
        if reader is not None:
            mine = (await db.execute(select(SlideVote).where(SlideVote.slide_id == slide.id,
                                                             SlideVote.user_id == reader.id))).scalar_one_or_none()
            my_vote = mine.as_good_as_it_can_be if mine else None
        anchor = catalog.anchor_record(slide) if result.node else None
        quality = catalog.quality_record(slide)
        shown = sorted(result.scores, key=lambda s: (s.depth, s.node))
        record = c.CommunityRecord(
            node=result.node, anchor=anchor, identifications=len(result.working), score=score, cutoff=CUTOFF,
            scores=[c.NodeScoreRecord(node=s.node, depth=s.depth, cumulative=s.cumulative,
                                      disagreements=s.disagreements, ancestor_disagreements=s.ancestor_disagreements,
                                      score=s.score) for s in shown],
            as_good_as_it_can_be=found.votes[0], needs_more=found.votes[1], my_vote=my_vote, badge=quality.badge)
        return c.IdentificationList(community=record, identifications=[
            identification_record(r, found.names, reader, found.categories.get(r.id)) for r in found.rows])

    @api.post("/slides/{slide_id}/identifications", status_code=201, response_model=c.IdentificationRecord)
    async def add_identification(slide_id: str, payload: IdentificationIn, request: Request, db: Db,
                                 user: Identifier) -> c.IdentificationRecord:
        try:
            row = await community.identify(db, request.app.state.gbif_client, user, slide_id, payload.anchor,
                                           payload.body, payload.disagreement)
        except community.CommunityRefused as exc:
            raise refused(exc) from exc
        return identification_record(row, {str(user.id): user.display_name}, user, None)

    @api.post("/identifications/{public_id}/withdraw", status_code=204)
    async def withdraw_identification(public_id: str, request: Request, db: Db, user: Identifier) -> Response:
        try:
            await community.withdraw(db, request.app.state.gbif_client, user, public_id)
        except community.CommunityRefused as exc:
            raise refused(exc) from exc
        return Response(status_code=204)

    @api.post("/identifications/{public_id}/restore", status_code=204)
    async def restore_identification(public_id: str, request: Request, db: Db, user: Identifier) -> Response:
        try:
            await community.restore(db, request.app.state.gbif_client, user, public_id)
        except community.CommunityRefused as exc:
            raise refused(exc) from exc
        return Response(status_code=204)

    @api.put("/slides/{slide_id}/vote", status_code=204)
    async def vote(slide_id: str, payload: VoteIn, request: Request, db: Db, user: Identifier) -> Response:
        try:
            await community.vote(db, request.app.state.gbif_client, user, slide_id, payload.as_good_as_it_can_be)
        except community.CommunityRefused as exc:
            raise refused(exc) from exc
        return Response(status_code=204)

    @api.get("/identify", response_model=c.SlidePage)
    async def identify_queue(
        request: Request, db: Db, reader: Reader,
        node: Annotated[str | None, Query(max_length=120)] = None,
        kind: Annotated[Literal["taxon", "rock", "mineral", "crystal", "material"] | None, Query()] = None,
        badge: Annotated[Literal["needs_id", "reference", "any"], Query()] = "needs_id",
        unidentified_by_me: bool = False,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=200)] = 48,
    ) -> c.SlidePage:
        """Published slides that need identification (or the reference ones), by collection and kind, oldest first
        so none waits forever (R-1307); optionally without those the signed-in account has identified."""
        conditions = [Slide.status == "published"]
        conditions.append(Slide.badge.in_(("needs_id", "reference")) if badge == "any" else Slide.badge == badge)
        if node:
            conditions.append((Slide.placement_node == node) | Slide.placement_node.startswith(node + "."))
        if kind:
            conditions.append(Slide.anchor_kind == kind)
        if unidentified_by_me and reader is not None:
            mine = select(Identification.slide_id).where(Identification.user_id == reader.id,
                                                         Identification.current.is_(True))
            conditions.append(Slide.id.not_in(mine))
        total = (await db.execute(select(func.count()).select_from(Slide).where(*conditions))).scalar_one()
        ids = (await db.execute(select(Slide.id).where(*conditions)
                                .order_by(Slide.published_at.asc(), Slide.id.asc())
                                .offset(offset).limit(limit))).scalars().all()
        rows = await slides.slides_by_ids(db, list(ids))
        order = {sid: i for i, sid in enumerate(ids)}
        rows.sort(key=lambda s: order[s.id])
        return c.SlidePage(items=[catalog.slide_summary(s, request.app.state.settings) for s in rows],
                           total=int(total), offset=offset, limit=limit)

    @api.post("/flags", status_code=201, response_model=c.FlagRecord)
    async def add_flag(payload: FlagIn, db: Db, user: Member) -> c.FlagRecord:
        try:
            return await moderation.flag(db, user, payload)
        except community.CommunityRefused as exc:
            raise refused(exc) from exc

    @api.get("/flags", response_model=list[c.FlagRecord])
    async def list_flags(db: Db, curator: Curator,
                         status: Annotated[Literal["open", "resolved", "all"], Query()] = "open") -> list[c.FlagRecord]:
        return await moderation.flags(db, status)

    @api.post("/flags/{public_id}/resolve", response_model=c.FlagRecord)
    async def resolve_flag(public_id: str, payload: ResolveIn, db: Db, curator: Curator) -> c.FlagRecord:
        try:
            return await moderation.resolve(db, curator, public_id, payload.resolution)
        except community.CommunityRefused as exc:
            raise refused(exc) from exc

    @api.post("/moderation/{kind}/{target_id}/hide", status_code=204)
    async def hide(kind: TargetKind, target_id: str, payload: ReasonIn, request: Request, db: Db,
                   curator: Curator) -> Response:
        try:
            await moderation.hide(db, request.app.state.gbif_client, curator, kind, target_id, payload.reason)
        except community.CommunityRefused as exc:
            raise refused(exc) from exc
        return Response(status_code=204)

    @api.post("/moderation/{kind}/{target_id}/unhide", status_code=204)
    async def unhide(kind: TargetKind, target_id: str, payload: ReasonIn, request: Request, db: Db,
                     curator: Curator) -> Response:
        try:
            await moderation.unhide(db, request.app.state.gbif_client, curator, kind, target_id, payload.reason)
        except community.CommunityRefused as exc:
            raise refused(exc) from exc
        return Response(status_code=204)

    @api.get("/moderation/actions", response_model=list[c.ModerationActionRecord])
    async def list_actions(db: Db, curator: Curator,
                           slide: Annotated[str | None, Query(max_length=16)] = None) -> list[c.ModerationActionRecord]:
        return await moderation.actions(db, slide)

    @api.get("/moderation/hidden", response_model=list[c.ModerationActionRecord])
    async def list_hidden(db: Db, curator: Curator) -> list[c.ModerationActionRecord]:
        """Every item hidden now, with the action that hid it."""
        hidden: list[c.ModerationActionRecord] = []
        latest: dict[tuple[str, str], c.ModerationActionRecord] = {}
        for action in reversed(await moderation.actions(db)):
            latest[(action.target_kind, action.target_id)] = action
        still = {("slide", s) for s in (await db.execute(select(Slide.short_id).where(Slide.status == "hidden")))
                 .scalars()}
        still |= {("identification", i) for i in (await db.execute(
            select(Identification.public_id).where(Identification.hidden.is_(True)))).scalars()}
        still |= {("annotation", a) for a in (await db.execute(
            select(Annotation.public_id).where(Annotation.hidden.is_(True)))).scalars()}
        for key, action in latest.items():
            if key in still and action.action == "hide":
                hidden.append(action)
        return hidden

    return [api]
