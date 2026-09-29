"""Profiles, cabinets, the export and the label sheets (U14).

| Route | Who |
|---|---|
| `GET /api/people/{handle}` | anyone: the profile, never the email |
| `GET /api/people/{handle}/slides`, `.../identifications` | anyone: the cabinet |
| `GET /api/people/me/slides.csv` | the signed-in account: its own slides with their exact places |
| `GET /api/labels/stocks` | anyone |
| `GET /api/labels/sheet.pdf?stock=&slides=&start=&dx=&dy=` | anyone, for published slides |
| `GET /api/labels/sheet.pdf?stock=&test=true` | anyone: the stock's test page |

Built per application, like the accounts routes, because the signed-in account comes from the settings' accounts.
"""
# No ``from __future__ import annotations``: the dependency aliases are defined inside ``routers`` and FastAPI must
# see them as objects.
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts.users import Accounts
from app.contracts import catalog as c
from app.db.models import User
from app.db.session import session
from app.labels import sheet
from app.labels.stocks import stocks
from app.services import catalog, people, slides

def stock_record(s) -> c.StockRecord:
    return c.StockRecord(id=s.id, name=c.LocalisedText(en=s.name, es=s.name_es), kind=s.kind, page=s.page,
                         width_mm=s.width, height_mm=s.height, columns=s.columns, rows=s.rows,
                         per_sheet=s.per_sheet, source=s.source, warnings=list(s.warnings))


def routers(accounts: Accounts) -> list[APIRouter]:
    api = APIRouter(prefix="/api", tags=["people"])
    Db = Annotated[AsyncSession, Depends(session)]
    Member = Annotated[User, Depends(accounts.current)]

    @api.get("/people/me/slides.csv")
    async def export_own(request: Request, db: Db, user: Member) -> Response:
        text = await people.export(db, user, request.app.state.settings)
        return Response(text, media_type="text/csv; charset=utf-8", headers={
            "Content-Disposition": f'attachment; filename="laminario-{user.handle or "slides"}.csv"',
            "Cache-Control": "no-store"})

    @api.get("/people/{handle}", response_model=c.ProfileRecord)
    async def read_profile(handle: str, db: Db) -> c.ProfileRecord:
        try:
            return await people.profile(db, handle)
        except people.PersonNotFound as exc:
            raise HTTPException(status_code=404, detail="no such person") from exc

    @api.get("/people/{handle}/slides", response_model=c.SlidePage)
    async def read_cabinet(handle: str, request: Request, db: Db,
                           collection: Annotated[str | None, Query(max_length=120)] = None,
                           offset: Annotated[int, Query(ge=0)] = 0,
                           limit: Annotated[int, Query(ge=1, le=200)] = 48) -> c.SlidePage:
        try:
            return await people.cabinet_slides(db, handle, request.app.state.settings, collection, offset, limit)
        except people.PersonNotFound as exc:
            raise HTTPException(status_code=404, detail="no such person") from exc

    @api.get("/people/{handle}/identifications", response_model=list[c.PersonIdentificationRecord])
    async def read_identifications(handle: str, request: Request, db: Db,
                                   offset: Annotated[int, Query(ge=0)] = 0,
                                   limit: Annotated[int, Query(ge=1, le=200)] = 48) -> list[
            c.PersonIdentificationRecord]:
        try:
            return await people.cabinet_identifications(db, handle, request.app.state.settings, offset, limit)
        except people.PersonNotFound as exc:
            raise HTTPException(status_code=404, detail="no such person") from exc

    @api.get("/labels/stocks", response_model=list[c.StockRecord])
    async def list_stocks() -> list[c.StockRecord]:
        return [stock_record(s) for s in stocks().values()]

    @api.get("/labels/sheet.pdf")
    async def label_sheet(
        request: Request,
        db: Db,
        stock: Annotated[str, Query(max_length=40)],
        slides_: Annotated[str, Query(alias="slides", max_length=6000)] = "",
        start: Annotated[int, Query(ge=0)] = 0,
        dx: Annotated[float, Query(ge=-10, le=10)] = 0.0,
        dy: Annotated[float, Query(ge=-10, le=10)] = 0.0,
        lang: Literal["en", "es"] = "en",
        test: bool = False,
    ) -> Response:
        """Labels for published slides on a stock, from a start position and a printer offset in mm; ``test=true``
        gives the stock's test page."""
        found = stocks().get(stock)
        if found is None:
            raise HTTPException(status_code=404, detail="no such label stock")
        if test:
            data = sheet.test_page(found, (dx, dy), lang)
            name = f"laminario-test-{found.id}.pdf"
        else:
            ids = [i for i in slides_.split(",") if i.strip()]
            if not ids:
                raise HTTPException(status_code=422, detail="name the slides to label")
            if len(ids) > sheet.MAX_SLIDES:
                raise HTTPException(status_code=422, detail=f"at most {sheet.MAX_SLIDES} slides per sheet")
            if start >= found.per_sheet:
                raise HTTPException(status_code=422, detail=f"the start position is 0 to {found.per_sheet - 1}")
            records, missing = [], []
            for raw in ids:
                row = await slides.get_slide(db, raw.strip())
                if row is None:
                    missing.append(raw.strip())
                else:
                    records.append(catalog.slide_record(row, request.app.state.settings))
            if missing:
                raise HTTPException(status_code=404, detail="no published slide: " + ", ".join(missing[:10]))
            data = sheet.render(records, found, start, (dx, dy), lang)
            name = f"laminario-labels-{found.id}.pdf"
        return Response(data, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{name}"'})

    return [api]
