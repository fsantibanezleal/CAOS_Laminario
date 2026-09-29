"""Slide cases: validate a submission, read a slide, list slides."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.collections import taxa
from app.collections.service import check_submission
from app.collections.places import DATA as PLACES_DATA
from app.collections.tree import load_tree
from app.contracts import catalog as c
from app.contracts.ingest import validate_submission
from app.db.session import session
from app.delivery import manifest as iiif_manifest
from app.services import catalog, explore, slides
from app.services.collections import host_view_slides

router = APIRouter(prefix="/api", tags=["slides"])
COUNTRY_SHAPES = PLACES_DATA / "countries.geojson"

NODE_QUERY = r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)*$"


@router.post(
    "/slide-cases/validate",
    response_model=c.ValidationResult,
    responses={422: {"model": c.ValidationResult, "description": "the submission breaks a rule of the contract"}},
)
async def validate_slide_case(payload: Annotated[Any, Body()], request: Request,
                              db: Annotated[AsyncSession, Depends(session)]) -> JSONResponse:
    """Run the ingestion contract and the tree's checks (anchor, part, host, placement) without storing a
    slide; a taxon seen for the first time is cached."""
    report = validate_submission(payload)
    if not report.valid:
        body = c.ValidationResult(valid=False, errors=report.errors)
        return JSONResponse(status_code=422, content=body.model_dump())
    try:
        checked = await check_submission(db, request.app.state.gbif_client, report.submission)
    except taxa.TaxonServiceUnavailable as exc:
        raise HTTPException(status_code=503, detail=f"the GBIF taxonomy did not answer; try again ({exc})") from exc
    await db.commit()
    if checked.errors:
        body = c.ValidationResult(valid=False, errors=checked.errors)
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


def explore_filters(
    node: Annotated[str | None, Query(max_length=120, pattern=NODE_QUERY)] = None,
    kind: Annotated[list[str] | None, Query(max_length=8)] = None,
    preparation: Annotated[list[str] | None, Query(max_length=12)] = None,
    modality: Annotated[list[str] | None, Query(max_length=12)] = None,
    preservation: Annotated[list[str] | None, Query(max_length=4)] = None,
    country: Annotated[list[str] | None, Query(max_length=40)] = None,
    licence: Annotated[list[str] | None, Query(max_length=8)] = None,
    wsi: bool | None = None,
    origin: Annotated[list[str] | None, Query(max_length=2)] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
) -> explore.Filters:
    """The filters of the Explore places, from the query string (a facet may repeat: ?preparation=smear&preparation=
    section)."""
    return explore.Filters(node=node, kind=explore.as_tuple(kind), preparation=explore.as_tuple(preparation),
                           modality=explore.as_tuple(modality), preservation=explore.as_tuple(preservation),
                           country=tuple(c.upper() for c in explore.as_tuple(country)),
                           licence=explore.as_tuple(licence), wsi=wsi, origin=explore.as_tuple(origin),
                           q=(q or "").strip() or None)


@router.get("/slides", response_model=c.SlidePage)
async def list_slides(
    request: Request,
    db: Annotated[AsyncSession, Depends(session)],
    filters: Annotated[explore.Filters, Depends(explore_filters)],
    sort: Annotated[str, Query(pattern="^(newest|name|relevance)$")] = "newest",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 48,
) -> c.SlidePage:
    """Published slides, filtered (node, anchor kind, preparation, modality, preservation, country, licence family,
    whole-slide, origin, text) and sorted (newest, name, or relevance to the text). Under a view (Parasites and
    hosts) they are the slides whose host lies inside the view's collection; there only the anchor kind filters."""
    settings = request.app.state.settings
    view = load_tree().get(filters.node) if filters.node else None
    if view is not None and view.is_view:
        shown = [s for s in await host_view_slides(db, load_tree(), view)
                 if not filters.kind or s.anchor_kind in filters.kind]
        rows, total = shown[offset:offset + limit], len(shown)
    else:
        ids, total = await explore.slide_ids(db, filters, sort, offset, limit)
        rows = await slides.slides_by_ids(db, ids)
    return c.SlidePage(items=[catalog.slide_summary(s, settings) for s in rows],
                       total=total, offset=offset, limit=limit)


@router.get("/explore/facets", response_model=c.FacetCounts)
async def slide_facets(db: Annotated[AsyncSession, Depends(session)],
                       filters: Annotated[explore.Filters, Depends(explore_filters)]) -> c.FacetCounts:
    """How many slides each facet value would match under the current filters."""
    return c.FacetCounts(**await explore.facet_counts(db, filters))


@router.get("/explore/map", response_model=c.MapRecord)
async def map_data(db: Annotated[AsyncSession, Depends(session)],
                   filters: Annotated[explore.Filters, Depends(explore_filters)]) -> c.MapRecord:
    """Countries with their slide counts and the points of slides with coordinates, after geoprivacy."""
    countries, points, total = await explore.map_data(db, filters)
    return c.MapRecord(countries=countries, total=total, points=[
        c.MapPointRecord(id=p.id, lat=p.lat, lon=p.lon, obscured=p.obscured,
                         cell=c.CellRecord(south=p.cell[0], west=p.cell[1], north=p.cell[2], east=p.cell[3])
                         if p.cell else None) for p in points])


@router.get("/explore/countries")
async def country_shapes() -> FileResponse:
    """The country shapes (Natural Earth 1:50m map units, public domain), for shading; they change only with a
    release."""
    return FileResponse(COUNTRY_SHAPES, media_type="application/geo+json",
                        headers={"Cache-Control": "public, max-age=86400"})


@router.get("/explore/basemap.pmtiles")
async def basemap(request: Request) -> FileResponse:
    """The world basemap (Protomaps, OpenStreetMap data, ODbL), read by the map with byte ranges. Absent when the
    extract is not installed: the map then draws the countries on their own."""
    path = request.app.state.settings.basemap
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="the basemap is not installed")
    return FileResponse(path, media_type="application/octet-stream",
                        headers={"Cache-Control": "public, max-age=604800"})


@router.get("/slides/{slide_id}/manifest")
async def read_manifest(slide_id: str, request: Request,
                        db: Annotated[AsyncSession, Depends(session)]) -> JSONResponse:
    """The slide as a IIIF Presentation 3 Manifest, for any IIIF viewer."""
    slide = await slides.get_slide(db, slide_id)
    if slide is None:
        raise HTTPException(status_code=404, detail="no published slide with this id")
    settings = request.app.state.settings
    document = iiif_manifest.manifest(catalog.slide_record(slide, settings), settings.public_base_url)
    return JSONResponse(document, media_type=iiif_manifest.MANIFEST_MEDIA_TYPE,
                        headers={"Access-Control-Allow-Origin": "*"})
