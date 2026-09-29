"""The taxon cache: lineages read from GBIF once (here, from the replay of recorded answers), then from the table."""

from __future__ import annotations

import asyncio
import os

import pytest

from app.collections import taxa
from app.db.engine import async_sessions, make_async_engine
from app.db.migrate import upgrade_to_head
from app.db.models import Taxon
from tests.delivery.support import free_port


def run(tmp_path, body):
    database = tmp_path / "laminario.sqlite3"
    upgrade_to_head(database)

    async def go():
        engine = make_async_engine(database)
        client = taxa.new_client(os.environ["LAMINARIO_GBIF_API_URL"])
        try:
            async with async_sessions(engine)() as db:
                return await body(db, client)
        finally:
            await client.aclose()
            await engine.dispose()

    return asyncio.run(go())


def test_lineage_is_fetched_once_and_cached(tmp_path):
    async def body(db, client):
        found = await taxa.lineage(db, client, 1032608)
        assert found.name == "Polyplax borealis" and found.rank == "species" and found.status == "accepted"
        assert found.ancestors == (1, 54, 216, 7612838, 4369, 1032563)
        facts = found.facts(part=None)
        assert facts.key == 1032608 and 7612838 in facts.lineage
        await db.commit()
        offline = taxa.new_client(f"http://127.0.0.1:{free_port()}/v1")
        try:
            again = await taxa.lineage(db, offline, 1032608)
        finally:
            await offline.aclose()
        assert again == found, "the second read comes from the table, not the network"
        assert (await db.get(Taxon, 1032608)).lineage_json == "[1, 54, 216, 7612838, 4369, 1032563]"

    run(tmp_path, body)


def test_synonyms_follow_their_accepted_taxon(tmp_path):
    async def body(db, client):
        found = await taxa.lineage(db, client, 112)
        assert found.status == "synonym" and found.accepted_key == 10707403
        assert found.effective_key == 10707403 and found.facts().key == 10707403
        assert 3 in found.keys, "the lineage is the accepted taxon's (kingdom Bacteria)"

    run(tmp_path, body)


def test_only_backbone_keys_resolve(tmp_path):
    async def body(db, client):
        assert await taxa.lineage(db, client, 298129616) is None, "a key from another checklist"
        assert await taxa.lineage(db, client, 999999999) is None, "a key GBIF does not know"

    run(tmp_path, body)


def test_an_unreachable_gbif_is_reported_not_guessed(tmp_path):
    async def body(db, _client):
        offline = taxa.new_client(f"http://127.0.0.1:{free_port()}/v1")
        try:
            with pytest.raises(taxa.TaxonServiceUnavailable):
                await taxa.lineage(db, offline, 2436436)
        finally:
            await offline.aclose()

    run(tmp_path, body)


def test_suggestions(tmp_path):
    async def body(_db, client):
        found = await taxa.suggest(client, "Polyplax")
        assert found[0]["name"] == "Polyplax" and found[0]["rank"] == "genus" and found[0]["ref"] == "1032563"
        assert "Psocodea" in found[0]["context"]
        assert all("polyplax" in item["name"].lower() for item in found), "GBIF also matches epithets"
        assert "Allostichaster polyplax" in [item["name"] for item in found]

    run(tmp_path, body)
