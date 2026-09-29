"""A contributor's slide cases (R-1205, R-1206).

| Route | Who |
|---|---|
| `GET /api/slide-cases` | a contributor: their own cases, newest first |
| `GET /api/slide-cases/{id}` | its contributor: the case as last sent, with each image's state |
| `PUT /api/slide-cases/{id}` | its contributor, while it is a draft: the new case, images it still names kept |
| `DELETE /api/slide-cases/{id}` | its contributor, while it is a draft, with its files |
| `POST /api/slide-cases/{id}/submit` | its contributor, once every image has its file |

Creating a case is `POST /api/slide-cases` (``app/routers/accounts.py``). Built per application, like the accounts
routes, because the signed-in account comes from the settings' accounts.
"""
# No ``from __future__ import annotations``: FastAPI must see the dependency aliases as objects.
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import roles
from app.accounts.users import Accounts
from app.collections import taxa
from app.collections.service import check_submission
from app.contracts import catalog as c
from app.contracts.ingest import validate_submission
from app.db.models import User
from app.db.session import session
from app.routers.accounts import requirement
from app.services import cases


def routers(accounts: Accounts) -> list[APIRouter]:
    api = APIRouter(prefix="/api/slide-cases", tags=["slide cases"])
    Db = Annotated[AsyncSession, Depends(session)]
    Contributor = Annotated[User, Depends(requirement(accounts, "submit"))]

    def refused(exc: cases.CaseRefused) -> HTTPException:
        return HTTPException(status_code=exc.status, detail=str(exc))

    @api.get("", response_model=list[c.CaseSummary])
    async def my_cases(db: Db, contributor: Contributor) -> list[c.CaseSummary]:
        return await cases.listing(db, contributor)

    @api.get("/{case_id}", response_model=c.CaseRecord)
    async def my_case(case_id: str, db: Db, contributor: Contributor) -> c.CaseRecord:
        try:
            return cases.record(await cases.owned(db, contributor, case_id))
        except cases.CaseRefused as exc:
            raise refused(exc) from None

    @api.put("/{case_id}", response_model=c.CaseRecord, responses={422: {"model": c.ValidationResult}})
    async def change_case(case_id: str, payload: Annotated[Any, Body()], request: Request, db: Db,
                          contributor: Contributor):
        report = validate_submission(payload)
        if not report.valid:
            return JSONResponse(status_code=422, content=c.ValidationResult(valid=False, errors=report.errors)
                                .model_dump())
        submission = report.submission
        if submission.origin != "contribution":
            raise HTTPException(status_code=403, detail="a contributor's case is a contribution")
        if submission.placement.override_reason and not roles.allowed(contributor.role, "override_placement"):
            raise HTTPException(status_code=403, detail="only a curator can override a placement")
        try:
            checked = await check_submission(db, request.app.state.gbif_client, submission)
        except taxa.TaxonServiceUnavailable as exc:
            raise HTTPException(status_code=503, detail=f"the GBIF taxonomy did not answer; try again ({exc})") from exc
        if checked.errors:
            await db.commit()
            return JSONResponse(status_code=422, content=c.ValidationResult(valid=False, errors=checked.errors)
                                .model_dump())
        try:
            case = await cases.replace(db, contributor, case_id, submission, checked.anchor,
                                       request.app.state.settings)
        except cases.CaseRefused as exc:
            raise refused(exc) from None
        return cases.record(case)

    @api.delete("/{case_id}", status_code=204)
    async def delete_case(case_id: str, request: Request, db: Db, contributor: Contributor) -> Response:
        try:
            await cases.remove(db, contributor, case_id, request.app.state.settings)
        except cases.CaseRefused as exc:
            raise refused(exc) from None
        return Response(status_code=204)

    @api.post("/{case_id}/submit", response_model=c.CaseRecord)
    async def submit_case(case_id: str, db: Db, contributor: Contributor) -> c.CaseRecord:
        try:
            return cases.record(await cases.submit(db, contributor, case_id))
        except cases.CaseRefused as exc:
            raise refused(exc) from None

    return [api]
