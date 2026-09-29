"""IIIF Image API 3: ``info.json`` with the public id and the asset's rights, and tiles from iipsrv.

A IIIF identifier is one percent-encoded path segment, but web servers decode ``%2F`` before routing, so a
storage key with slashes arrives as several segments. The routes therefore take the whole path and read it
from the end: ``.../info.json`` is the service description, four trailing segments that are a valid region,
size, rotation and quality.format are an image request, and anything else is the base URI.
"""

from __future__ import annotations

import re
from typing import Annotated

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import licences
from app.db.session import session
from app.delivery import iiif
from app.services import slides

router = APIRouter(tags=["iiif"])

CORS = {"Access-Control-Allow-Origin": "*"}
PASSED_HEADERS = ("content-type", "last-modified", "etag", "cache-control")
#: A storage key: the slide's short id, then the content-addressed file name.
MEDIA_KEY = re.compile(r"[A-Za-z0-9]{8}/[A-Za-z0-9._-]+")

_NUMBER = r"\d+(?:\.\d+)?"
REGION = re.compile(rf"^(?:full|square|\d+,\d+,\d+,\d+|pct:{_NUMBER},{_NUMBER},{_NUMBER},{_NUMBER})$")
SIZE = re.compile(rf"^\^?(?:max|\d+,|,\d+|!?\d+,\d+|pct:{_NUMBER})$")
ROTATION = re.compile(rf"^!?{_NUMBER}$")
QUALITY_FORMAT = re.compile(r"^(?:default|color|gray|bitonal)\.(?:jpg|png|webp|tif)$")


def parse(path: str) -> tuple[str, str, tuple[str, str, str, str] | None]:
    """(kind, storage key, image parameters) for a path under ``/iiif/``; kind is info, image or base."""
    segments = path.split("/")
    if segments[-1] == "info.json" and len(segments) > 1:
        return "info", "/".join(segments[:-1]), None
    if len(segments) >= 5:
        region, size, rotation, quality = segments[-4:]
        if REGION.match(region) and SIZE.match(size) and ROTATION.match(rotation) and QUALITY_FORMAT.match(quality):
            return "image", "/".join(segments[:-4]), (region, size, rotation, quality)
    return "base", path, None


async def _public(key_text: str, db: AsyncSession):
    key = iiif.storage_key(key_text)
    if key is None:
        raise HTTPException(status_code=404, detail="not an image identifier")
    asset = await slides.get_public_pyramid(db, key)
    if asset is None:
        raise HTTPException(status_code=404, detail="no published image with this identifier")
    return key, asset


async def _upstream_info(request: Request, key: str) -> dict:
    cache: iiif.InfoCache = request.app.state.iiif_info_cache
    cached = cache.get(key)
    if cached is not None:
        return cached
    client: httpx2.AsyncClient = request.app.state.tile_client
    try:
        response = await client.get(iiif.upstream_path(key) + "/info.json")
    except httpx2.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"the tile server did not answer: {type(exc).__name__}") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"the tile server answered {response.status_code}")
    document = response.json()
    cache.put(key, document)
    return document


@router.get("/iiif/{path:path}")
async def iiif_request(path: str, request: Request, db: Annotated[AsyncSession, Depends(session)]) -> Response:
    """The Image API: info.json from the API, image requests from iipsrv, the base URI redirected."""
    kind, key_text, params = parse(path)
    if kind == "base":
        key = iiif.storage_key(key_text)
        if key is None:
            raise HTTPException(status_code=404, detail="not an image identifier")
        return RedirectResponse(url=f"/iiif/{iiif.identifier(key)}/info.json", status_code=303, headers=CORS)
    key, asset = await _public(key_text, db)
    if kind == "info":
        upstream = await _upstream_info(request, key)
        settings = request.app.state.settings
        info = iiif.rewrite_info(upstream, iiif.public_service_id(settings.public_base_url, key),
                                 licences.iiif_rights(asset.licence_uri))
        return JSONResponse(info, media_type=iiif.INFO_MEDIA_TYPE, headers=CORS)
    client: httpx2.AsyncClient = request.app.state.tile_client
    try:
        upstream = await client.get(f"{iiif.upstream_path(key)}/{'/'.join(params)}")
    except httpx2.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"the tile server did not answer: {type(exc).__name__}") from exc
    headers = {k: v for k, v in upstream.headers.items() if k.lower() in PASSED_HEADERS} | CORS
    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers)


@router.get("/media/{key:path}")
async def media(key: str, request: Request, db: Annotated[AsyncSession, Depends(session)]) -> FileResponse:
    """A plain image of a published slide (a macro photograph, a height map) by its storage key. Keys are content
    addresses, so the answer never changes: it is cached for a year. nginx passes /media/ here and caches it."""
    if not MEDIA_KEY.fullmatch(key) or ".." in key:
        raise HTTPException(status_code=404, detail="not an image of a published slide")
    asset = await slides.get_public_image(db, key)
    root = request.app.state.settings.store_root.resolve()
    path = (root / key).resolve()
    if asset is None or not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail="not an image of a published slide")
    return FileResponse(path, media_type="image/jpeg" if path.suffix == ".jpg" else None,
                        headers={"Cache-Control": "public, max-age=31536000, immutable", **CORS})


@router.get("/api/_internal/iiif-access/{key:path}", status_code=204, include_in_schema=False)
async def iiif_access(key: str, db: Annotated[AsyncSession, Depends(session)]) -> Response:
    """nginx's check before it serves a tile: 204 for a published image, 403 otherwise.

    nginx's ``auth_request`` reads 401 and 403 as a refusal and any other status as an error, hence 403.
    nginx blocks this path from outside.
    """
    stored = iiif.storage_key(key)
    if stored is None or await slides.get_public_pyramid(db, stored) is None:
        return Response(status_code=403)
    return Response(status_code=204)
