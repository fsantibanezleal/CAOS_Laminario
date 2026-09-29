"""Explore: filters, facet counts, text search and the map, over slides seeded through the product's own service."""

from __future__ import annotations

import asyncio

from app.contracts.ingest import SlideCaseSubmission
from app.db.base import utcnow
from app.db.engine import async_sessions, make_async_engine
from app.db.migrate import upgrade_to_head
from app.services import slides
from tests import payloads
from tests.accounts.support import app_client, settings_for

LOUSE = "life.insects.lice"


def seed(settings, variants: list[dict]) -> list[str]:
    """Published slides from the standard contribution, each changed as a variant says."""
    database = settings.data_root / "laminario.sqlite3"
    upgrade_to_head(database)

    async def run() -> list[str]:
        engine = make_async_engine(database)
        ids = []
        try:
            async with async_sessions(engine)() as session:
                for v in variants:
                    payload = payloads.contribution()
                    payload["slide"]["preparation"] = v.get("preparation", "whole_mount")
                    payload["slide"]["catalogue_number"] = v.get("catalogue", "LAM-0001")
                    payload["specimen"]["geoprivacy"] = v.get("geoprivacy", "open")
                    if "coordinates" in v:
                        payload["specimen"]["coordinates"] = v["coordinates"]
                    if v.get("country"):
                        payload["specimen"].pop("coordinates", None)
                        payload["specimen"]["country"] = v["country"]
                    payload["assets"][1]["modality"] = v.get("modality", "brightfield")
                    payload["assets"][1]["licence"] = v.get("licence", "https://creativecommons.org/licenses/by/4.0/")
                    slide = await slides.create_slide(session, SlideCaseSubmission.model_validate(payload),
                                                      contributor_id="user-1")
                    for asset in slide.assets:
                        asset.status = "ready"
                        if v.get("wsi") and asset.family == "micro":
                            asset.role = "pyramid"
                    slide.status = "published"
                    slide.published_at = utcnow()
                    await session.commit()
                    ids.append(slide.short_id)
        finally:
            await engine.dispose()
        return ids

    return asyncio.run(run())


VARIANTS = [
    {"preparation": "whole_mount", "catalogue": "NHMUK010173454"},
    {"preparation": "smear", "modality": "darkfield", "country": "GP"},
    {"preparation": "section", "wsi": True, "licence": "https://creativecommons.org/licenses/by-sa/4.0/"},
    {"preparation": "smear", "geoprivacy": "obscured"},
    {"preparation": "section", "geoprivacy": "private"},
]


def test_filters_facets_search_and_map(tmp_path):
    settings = settings_for(tmp_path)
    ids = seed(settings, VARIANTS)
    with app_client(settings) as client:
        everything = client.get("/api/slides", params={"node": "life.insects"}).json()
        assert everything["total"] == 5

        smears = client.get("/api/slides", params={"preparation": "smear"}).json()
        assert {s["id"] for s in smears["items"]} == {ids[1], ids[3]}
        both = client.get("/api/slides", params=[("preparation", "smear"), ("preparation", "section")]).json()
        assert both["total"] == 4
        assert client.get("/api/slides", params={"modality": "darkfield"}).json()["items"][0]["id"] == ids[1]
        assert [s["id"] for s in client.get("/api/slides", params={"wsi": "true"}).json()["items"]] == [ids[2]]
        assert client.get("/api/slides", params={"licence": "by-sa"}).json()["total"] == 1
        assert [s["id"] for s in client.get("/api/slides", params={"country": "gp"}).json()["items"]] == [ids[1]]

        # The facet's own filter is left out of its counts, so the other preparations still show what they add.
        facets = client.get("/api/explore/facets", params={"preparation": "smear"}).json()
        assert facets["preparation"] == {"whole_mount": 1, "smear": 2, "section": 2}
        assert facets["modality"] == {"brightfield": 1, "darkfield": 1}
        assert facets["country"] == {"CL": 1, "GP": 1}

        # Search: Spanish node names without their accents, prefixes, the catalogue number, the short id.
        assert client.get("/api/slides", params={"q": "piojos"}).json()["total"] == 5
        assert client.get("/api/slides", params={"q": "insect"}).json()["total"] == 5
        assert client.get("/api/slides", params={"q": "Guadalupe"}).json()["items"][0]["id"] == ids[1]
        catalogue = client.get("/api/slides", params={"q": "NHMUK010173454", "sort": "relevance"}).json()
        assert [s["id"] for s in catalogue["items"]] == [ids[0]]
        assert client.get("/api/slides", params={"q": ids[2]}).json()["items"][0]["id"] == ids[2]
        assert client.get("/api/slides", params={"q": '" OR NEAR('}).status_code == 200  # never parsed as syntax

        # The summary carries the label end the drawer draws.
        summary = next(s for s in everything["items"] if s["id"] == ids[1])
        assert summary["label"] == {"catalogue_number": "LAM-0001", "collected_on": "2019-04-20",
                                    "locality_text": "Near a stream", "country": "GP"}

        # The map: the open slide at its point, the obscured one in its cell, the private one nowhere.
        world = client.get("/api/explore/map").json()
        assert world["total"] == 5 and world["countries"] == {"CL": 4, "GP": 1}
        points = {p["id"]: p for p in world["points"]}
        assert set(points) == {ids[0], ids[2], ids[3]}
        assert points[ids[0]]["lat"] == -33.4489 and not points[ids[0]]["obscured"]
        obscured = points[ids[3]]
        assert obscured["obscured"] and obscured["cell"]["south"] <= obscured["lat"] <= obscured["cell"]["north"]
        assert (obscured["lat"], obscured["lon"]) != (-33.4489, -70.6693)

        shapes = client.get("/api/explore/countries")
        assert shapes.status_code == 200 and shapes.headers["cache-control"] == "public, max-age=86400"
        assert len(shapes.json()["features"]) == 247
