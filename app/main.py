"""The FastAPI application. Routes are added unit by unit."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.accounts.users import build as build_accounts
from app.collections import taxa
from app.config import Settings, get_settings
from app.db.engine import async_sessions, database_path, make_async_engine, make_sync_engine
from app.delivery.iiif import InfoCache
from app.routers import about, accounts, annotations, cases, collections, community, iiif, jobs, people, slides, uploads
from app.version import VERSION


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_async_engine(database_path(settings))
        app.state.engine = engine
        app.state.sessions = async_sessions(engine)
        app.state.sync_engine = make_sync_engine(database_path(settings))  # the job queue's writes
        app.state.tile_client = httpx2.AsyncClient(base_url=settings.iipsrv_url, timeout=30.0)
        app.state.iiif_info_cache = InfoCache()
        app.state.gbif_client = taxa.new_client(settings.gbif_api_url)
        try:
            yield
        finally:
            await app.state.gbif_client.aclose()
            await app.state.tile_client.aclose()
            app.state.sync_engine.dispose()
            await engine.dispose()

    app = FastAPI(
        title="Laminario",
        version=VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Liveness plus identity: gates check they are talking to Laminario, at this version."""
        return {"status": "ok", "product": "laminario", "version": VERSION}

    app.state.accounts = build_accounts(settings)
    trusted = allowed_origins(settings)

    @app.middleware("http")
    async def same_origin_writes(request: Request, call_next):
        """A browser always sends Origin on cross-site writes; refuse any that is not this site.

        Session cookies are SameSite=Lax, which already keeps them off cross-site POSTs from pages; this closes the
        rest (a request without cookies is anonymous anyway, and non-browser clients send no Origin).
        """
        origin = request.headers.get("origin")
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and origin and origin not in trusted:
            return JSONResponse(status_code=403, content={"detail": "cross-site request refused"})
        return await call_next(request)

    for router in [*accounts.routers(app.state.accounts), *uploads.routers(app.state.accounts),
                   *annotations.routers(app.state.accounts), *cases.routers(app.state.accounts),
                   *community.routers(app.state.accounts), *people.routers(app.state.accounts)]:
        app.include_router(router)
    app.include_router(slides.router)
    app.include_router(iiif.router)
    app.include_router(jobs.router)
    app.include_router(collections.router)
    app.include_router(about.router)
    return app



DEV_ORIGINS = ("http://127.0.0.1:5909", "http://localhost:5909", "http://127.0.0.1:4909", "http://localhost:4909")


def allowed_origins(settings: Settings) -> set[str]:
    """This site's origin, plus the web dev and preview servers outside production."""
    from urllib.parse import urlsplit

    parts = urlsplit(settings.public_base_url)
    origins = {f"{parts.scheme}://{parts.netloc}"}
    if settings.env != "production":
        origins |= set(DEV_ORIGINS)
    return origins


app = create_app()
