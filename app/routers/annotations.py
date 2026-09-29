"""Annotations on the stage (R-1108).

| Route | Who |
|---|---|
| `GET /api/slides/{id}/assets/{asset}/annotations` | anyone, on a published slide |
| `POST /api/slides/{id}/assets/{asset}/annotations` | a signed-in account (the ``annotate`` capability) |
| `DELETE /api/annotations/{annotation}` | its author, or a curator |

Built per application, like the accounts routes, because the signed-in account comes from the settings' accounts.
"""
# No ``from __future__ import annotations``: the dependency aliases are defined inside ``routers`` and FastAPI must
# see them as objects.
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.users import Accounts
from app.contracts import catalog as c
from app.contracts.annotations import AnnotationIn
from app.db.models import User
from app.db.session import session
from app.routers.accounts import requirement
from app.services import annotations, slides


def routers(accounts: Accounts) -> list[APIRouter]:
    api = APIRouter(prefix="/api", tags=["annotations"])
    Db = Annotated[AsyncSession, Depends(session)]
    Annotator = Annotated[User, Depends(requirement(accounts, "annotate"))]
    Reader = Annotated[User | None, Depends(accounts.optional)]

    async def slide_and_asset(db: AsyncSession, slide_id: str, asset_id: int):
        slide = await slides.get_slide(db, slide_id)
        asset = await annotations.published_asset(db, slide, asset_id) if slide else None
        if slide is None or asset is None:
            raise HTTPException(status_code=404, detail="no such image on a published slide")
        return slide, asset

    @api.get("/slides/{slide_id}/assets/{asset_id}/annotations", response_model=list[c.AnnotationRecord])
    async def list_annotations(slide_id: str, asset_id: int, request: Request, db: Db,
                               reader: Reader) -> list[c.AnnotationRecord]:
        slide, asset = await slide_and_asset(db, slide_id, asset_id)
        return await annotations.listing(db, slide, asset, request.app.state.settings, reader)

    @api.post("/slides/{slide_id}/assets/{asset_id}/annotations", status_code=201,
              response_model=c.AnnotationRecord)
    async def add_annotation(slide_id: str, asset_id: int, payload: AnnotationIn, request: Request, db: Db,
                             author: Annotator) -> c.AnnotationRecord:
        slide, asset = await slide_and_asset(db, slide_id, asset_id)
        try:
            return await annotations.create(db, slide, asset, payload, author, request.app.state.settings)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @api.delete("/annotations/{public_id}", status_code=204)
    async def remove_annotation(public_id: str, db: Db, user: Annotator) -> Response:
        row = await annotations.by_public_id(db, public_id)
        if row is None:
            raise HTTPException(status_code=404, detail="no such annotation")
        if not annotations.may_remove(row, user):
            raise HTTPException(status_code=403, detail="only its author or a curator removes an annotation")
        await db.delete(row)
        await db.commit()
        return Response(status_code=204)

    return [api]
