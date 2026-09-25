"""Slide cases: validate a submission, read a slide, list slides."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import catalog as c
from app.contracts.ingest import validate_submission
from app.db.session import session
from app.services import catalog, slides

router = APIRouter(prefix="/api", tags=["slides"])

NODE_QUERY = r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)*$"


@router.post(
    "/slide-cases/validate",
    response_model=c.ValidationResult,
    responses={422: {"model": c.ValidationResult, "description": "the submission breaks a rule of the contract"}},
)
async def validate_slide_case(payload: Annotated[Any, Body()]) -> JSONResponse:
    """Run the ingestion contract on a slide case without storing anything."""
    report = validate_submission(payload)
    if not report.valid:
        body = c.ValidationResult(valid=False, errors=report.errors)
        return JSONResponse(status_code=422, content=body.model_dump())
    return JSONResponse(status_code=200, content=c.ValidationResult(valid=True, flags=report.flags).model_dump())


@router.get("/slides/{slide_id}", response_model=c.SlideRecord)
async def read_slide(slide_id: str, request: Request,
                     db: Annotated[AsyncSession, Depends(session)]) -> c.SlideRecord:
    """A published slide by its short id; case and look-alike letters are forgiven."""
    slide = await slides.get_slide(db, slide_id)
    if slide is None:
        raise HTTPException(status_code=404, detail="no published slide with this id")
    return catalog.slide_record(slide, request.app.state.settings)


@router.get("/slides", response_model=c.SlidePage)
async def list_slides(
    request: Request,
    db: Annotated[AsyncSession, Depends(session)],
    node: Annotated[str | None, Query(max_length=120, pattern=NODE_QUERY)] = None,
    kind: Annotated[str | None, Query(pattern="^(taxon|rock|mineral|crystal|material)$")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 48,
) -> c.SlidePage:
    """Published slides, newest first, optionally under a collection node or of one anchor kind."""
    rows, total = await slides.list_slides(db, node=node, kind=kind, offset=offset, limit=limit)
    settings = request.app.state.settings
    return c.SlidePage(items=[catalog.slide_summary(s, settings) for s in rows],
                       total=total, offset=offset, limit=limit)
