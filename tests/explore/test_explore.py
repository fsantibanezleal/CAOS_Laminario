"""Explore: filters, facet counts, text search and the map, over slides seeded through the product's own service."""

from __future__ import annotations

import asyncio

import pytest

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
                    if v.get("node"):
                        payload["placement"]["node"] = v["node"]
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
    {"preparation": "section", "node": "life.plants"},
]


@pytest.fixture(scope="module")
def explore(tmp_path_factory):
    """A client over six published slides: five lice and one plant."""
    settings = settings_for(tmp_path_factory.mktemp("explore"))
    ids = seed(settings, VARIANTS)
    with app_client(settings) as client:
        yield client, ids


def test_filters_and_facet_counts(explore):
    client, ids = explore
    everything = client.get("/api/slides", params={"node": "life.insects"}).json()
    assert everything["total"] == 5
    assert client.get("/api/slides").json()["total"] == 6

    smears = client.get("/api/slides", params={"preparation": "smear"}).json()
    assert {s["id"] for s in smears["items"]} == {ids[1], ids[3]}
    both = client.get("/api/slides", params=[("preparation", "smear"), ("preparation", "section")]).json()
    assert both["total"] == 5
    assert client.get("/api/slides", params={"modality": "darkfield"}).json()["items"][0]["id"] == ids[1]
    assert [s["id"] for s in client.get("/api/slides", params={"wsi": "true"}).json()["items"]] == [ids[2]]
    assert client.get("/api/slides", params={"licence": "by-sa"}).json()["total"] == 1
    assert [s["id"] for s in client.get("/api/slides", params={"country": "gp"}).json()["items"]] == [ids[1]]

    # The facet's own filter is left out of its counts, so the other preparations still show what they add.
    facets = client.get("/api/explore/facets", params={"preparation": "smear", "node": "life.insects"}).json()
    assert facets["preparation"] == {"whole_mount": 1, "smear": 2, "section": 2}
    assert facets["modality"] == {"brightfield": 1, "darkfield": 1}
    assert facets["country"] == {"CL": 1, "GP": 1}
    # Under an asset filter, the facets that join the assets themselves still count (found by the walk: a 500).
    darkfield = client.get("/api/explore/facets", params={"modality": "darkfield"})
    assert darkfield.status_code == 200, darkfield.text
    assert darkfield.json()["modality"] == {"brightfield": 5, "darkfield": 1}
    assert sum(darkfield.json()["licence"].values()) >= 1
    by_sa = client.get("/api/explore/facets", params={"licence": "by-sa"})
    assert by_sa.status_code == 200 and sum(by_sa.json()["modality"].values()) == 1
    # The collection facet leaves the node out: the smears are all lice, but a search sees every cabinet.
    assert facets["collection"] == {"life.insects": 2}
    assert client.get("/api/explore/facets", params={"node": "life.insects"}).json()["collection"] == {
        "life.insects": 5, "life.plants": 1}

    # The summary carries the label end the drawer draws.
    summary = next(s for s in everything["items"] if s["id"] == ids[1])
    assert summary["label"] == {"catalogue_number": "LAM-0001", "collected_on": "2019-04-20",
                                "locality_text": "Near a stream", "country": "GP"}


def test_search(explore):
    client, ids = explore
    # Spanish node names without their accents, prefixes, the catalogue number, the short id.
    assert client.get("/api/slides", params={"q": "piojos"}).json()["total"] == 5
    assert client.get("/api/slides", params={"q": "insect"}).json()["total"] == 5
    assert client.get("/api/slides", params={"q": "Guadalupe"}).json()["items"][0]["id"] == ids[1]
    assert client.get("/api/slides", params={"q": "plantas"}).json()["total"] == 1
    catalogue = client.get("/api/slides", params={"q": "NHMUK010173454", "sort": "relevance"}).json()
    assert [s["id"] for s in catalogue["items"]] == [ids[0]]
    assert client.get("/api/slides", params={"q": ids[2]}).json()["items"][0]["id"] == ids[2]
    assert client.get("/api/slides", params={"q": '" OR NEAR('}).status_code == 200  # never parsed as syntax
    assert client.get("/api/slides", params={"q": "piojos", "node": "life.plants"}).json()["total"] == 0


def test_map_after_geoprivacy(explore):
    client, ids = explore
    # The open slide at its point, the obscured one in its cell, the private one nowhere.
    world = client.get("/api/explore/map").json()
    assert world["total"] == 6 and world["countries"] == {"CL": 5, "GP": 1}
    points = {p["id"]: p for p in world["points"]}
    assert set(points) == {ids[0], ids[2], ids[3], ids[5]}
    assert points[ids[0]]["lat"] == -33.4489 and not points[ids[0]]["obscured"]
    obscured = points[ids[3]]
    assert obscured["obscured"] and obscured["cell"]["south"] <= obscured["lat"] <= obscured["cell"]["north"]
    assert (obscured["lat"], obscured["lon"]) != (-33.4489, -70.6693)

    names = client.get("/api/explore/country-names").json()["countries"]
    assert names["GP"] == {"en": "Guadeloupe", "es": "Guadalupe"} and len(names) == 257

    shapes = client.get("/api/explore/countries")
    assert shapes.status_code == 200 and shapes.headers["cache-control"] == "public, max-age=86400"
    features = shapes.json()["features"]
    assert len(features) == 247
    chile = next(f for f in features if f["id"] == "CL")
    assert chile["properties"]["label"] == [-72.32, -38.15] and chile["properties"]["label_zoom"] == 1.7
