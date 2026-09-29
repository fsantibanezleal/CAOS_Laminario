"""About the collection (U15): ``GET /api/about``, the numbers counted when it is read and the credits."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import catalog as c
from app.db.session import session
from app.services import about

router = APIRouter(prefix="/api", tags=["about"])
Db = Annotated[AsyncSession, Depends(session)]


@router.get("/about", response_model=c.AboutRecord)
async def read_about(response: Response, db: Db) -> c.AboutRecord:
    # Counts change as slides are published; a minute of caching spares the database a burst of readers.
    response.headers["Cache-Control"] = "public, max-age=60"
    return await about.about(db)
