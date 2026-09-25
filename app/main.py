"""The FastAPI application. Routes are added unit by unit."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.db.engine import async_sessions, database_path, make_async_engine
from app.routers import slides
from app.version import VERSION


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_async_engine(database_path(settings))
        app.state.engine = engine
        app.state.sessions = async_sessions(engine)
        try:
            yield
        finally:
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

    app.include_router(slides.router)
    return app


app = create_app()
