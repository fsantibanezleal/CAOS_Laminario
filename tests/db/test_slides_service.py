"""Storing a validated case and reading it back through the API."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.contracts.ingest import SlideCaseSubmission
from app.db.engine import async_sessions, make_async_engine
from app.db.migrate import upgrade_to_head
from app.main import create_app
from app.services import slides
from tests import payloads


def make_settings(tmp_path: Path) -> Settings:
    return Settings(public_base_url="https://laminario.example.org", data_root=tmp_path / "data")


async def _store(settings: Settings, publish: bool, generate=None) -> str:
    engine = make_async_engine(settings.data_root / "laminario.sqlite3")
    try:
        async with async_sessions(engine)() as session:
            sub = SlideCaseSubmission.model_validate(payloads.contribution())
            kwargs = {"generate": generate} if generate else {}
            slide = await slides.create_slide(session, sub, contributor_id="user-1", **kwargs)
            if publish:
                slide.status = "published"
                from app.db.base import utcnow
                slide.published_at = utcnow()
                for asset in slide.assets:
                    asset.status = "ready"
                    asset.storage_key = f"store/{slide.short_id}/{asset.id}.tif"
                await session.commit()
            return slide.short_id
    finally:
        await engine.dispose()


def test_create_read_and_list(tmp_path: Path):
    settings = make_settings(tmp_path)
    upgrade_to_head(settings.data_root / "laminario.sqlite3")
    draft_id = asyncio.run(_store(settings, publish=False))
    published_id = asyncio.run(_store(settings, publish=True))

    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/slides/{draft_id}").status_code == 404, "a draft is not public"
        assert client.get("/api/slides/NOTANID").status_code == 404

        record = client.get(f"/api/slides/{published_id.lower()}").json()
        assert record["id"] == published_id
        assert record["permalink"] == f"https://laminario.example.org/s/{published_id}"
        assert record["place"]["point"] == {"lat": -33.4489, "lon": -70.6693}
        assert [a["family"] for a in record["assets"]] == ["macro", "micro"]
        assert record["assets"][1]["media"]["iiif_info_url"].startswith("https://laminario.example.org/iiif/")
        assert record["assets"][1]["media"]["iiif_info_url"].endswith("/info.json")

        page = client.get("/api/slides", params={"node": "life.insects"}).json()
        assert page["total"] == 1 and page["items"][0]["id"] == published_id
        assert page["items"][0]["thumbnail_url"].endswith("/full/!320,320/0/default.jpg")
        assert client.get("/api/slides", params={"node": "earth"}).json()["total"] == 0
        assert client.get("/api/slides", params={"kind": "rock"}).json()["total"] == 0
        assert client.get("/api/slides", params={"node": "Life/Insects"}).status_code == 422


def test_short_id_collision_is_retried(tmp_path: Path):
    settings = make_settings(tmp_path)
    upgrade_to_head(settings.data_root / "laminario.sqlite3")
    first = asyncio.run(_store(settings, publish=False))
    sequence = iter([first, first, "ZZZZZZZ1"])
    second = asyncio.run(_store(settings, publish=False, generate=lambda: next(sequence)))
    assert second == "ZZZZZZZ1"
