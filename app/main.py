"""The FastAPI application. Routes are added unit by unit; U0 provides the health endpoint."""

from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings
from app.version import VERSION


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Laminario",
        version=VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.settings = settings

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Liveness plus identity: gates check they are talking to Laminario, at this version."""
        return {"status": "ok", "product": "laminario", "version": VERSION}

    return app


app = create_app()
