"""R-1301 and R-1309: identifications on a published slide, one current per account, withdrawn and restored; every
published slide carries its first identification (the contributor's, or the source's for a base slide)."""

from __future__ import annotations

from app.community import store
from app.db.engine import database_path, make_sync_engine
from tests.accounts.support import app_client, settings_for

from .support import (POLYPLAX, POLYPLAX_ALASKENSIS, POLYPLAX_BOREALIS, community, identify, people, published,
                      sql)


def test_identifications_one_current_per_account(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"])

        # R-1309: the contributor's anchor is the first identification.
        first = community(client, sid, p["maker"])
        assert len(first["identifications"]) == 1
        own = first["identifications"][0]
        assert own["mine"] and own["by"] == "Test Person" and own["anchor"]["ref"] == "1032608"
        assert first["community"]["node"] is None and first["community"]["badge"] == "needs_id"

        # Roles: a visitor and a contributor may read but not identify; a draft is not a slide to identify.
        assert identify(client, sid, {}, POLYPLAX_BOREALIS).status_code == 401
        assert identify(client, sid, p["maker"], POLYPLAX_BOREALIS).status_code == 403
        assert identify(client, "ZZZZZZZZ", p["one"], POLYPLAX_BOREALIS).status_code == 404

        # An agreeing identification: the community reaches the species and the slide is verified.
        agreed = identify(client, sid, p["one"], POLYPLAX_BOREALIS, body="Setae as in Ferris 1932")
        assert agreed.status_code == 201, agreed.text
        now = community(client, sid)
        assert now["community"]["node"] == "taxon:1032608" and now["community"]["badge"] == "verified"
        assert now["community"]["score"] == 1.0 and now["community"]["identifications"] == 2
        assert {i["category"] for i in now["identifications"]} == {"improving", "supporting"}

        # A second identification by the same account supersedes the first (one current per account).
        again = identify(client, sid, p["one"], POLYPLAX_ALASKENSIS)
        assert again.status_code == 201
        rows = sql(settings, "SELECT i.anchor_ref, i.current FROM identification i JOIN slide s ON s.id = i.slide_id "
                             "WHERE s.short_id = :s AND i.user_id IS NOT NULL ORDER BY i.id", s=sid)
        assert [(r.anchor_ref, bool(r.current)) for r in rows] == [
            ("1032608", True), ("1032608", False), ("1032575", True)]
        assert community(client, sid)["community"]["node"] == "taxon:1032563"  # the genus: one against one

        # Withdrawn, it no longer counts; restored, it counts again; only its account does either.
        latest = agreed.json()["id"], again.json()["id"]
        assert client.post(f"/api/identifications/{latest[1]}/withdraw", headers=p["two"]).status_code == 404
        assert client.post(f"/api/identifications/{latest[1]}/withdraw", headers=p["one"]).status_code == 204
        assert community(client, sid)["community"]["node"] is None
        assert client.post(f"/api/identifications/{latest[0]}/restore", headers=p["one"]).status_code == 204
        restored = community(client, sid)
        assert restored["community"]["node"] == "taxon:1032608"
        assert [i["current"] for i in restored["identifications"] if i["id"] in latest] == [True, False]


def test_an_ancestor_says_whether_it_disagrees(tmp_path):
    """R-1302 through the API: naming the genus of a species asks whether the identifier disagrees."""
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"])
        unstated = identify(client, sid, p["one"], POLYPLAX)
        assert unstated.status_code == 422 and unstated.json()["detail"]["code"] == "disagreement_unstated"
        assert identify(client, sid, p["one"], POLYPLAX, disagreement=False).status_code == 201
        assert identify(client, sid, p["two"], POLYPLAX_BOREALIS).status_code == 201
        # One for the species, the genus without disagreeing: the species holds (2 of 2 for it, the genus for all).
        assert community(client, sid)["community"]["node"] == "taxon:1032608"
        assert identify(client, sid, p["three"], POLYPLAX, disagreement=True).status_code == 201
        # A disagreeing genus: the species scores 2 / (2 + 0 + 1), not above two thirds; the genus wins.
        result = community(client, sid)["community"]
        assert result["node"] == "taxon:1032563"
        species = next(s for s in result["scores"] if s["node"] == "taxon:1032608")
        assert (species["cumulative"], species["ancestor_disagreements"]) == (2, 1)
        unknown = identify(client, sid, p["one"], {"kind": "taxon", "ref": "999999999", "name": "Nothing"})
        assert unknown.status_code == 422 and unknown.json()["detail"]["code"] == "taxon_unknown"


def test_a_base_slide_carries_the_sources_determination(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"])
        # Made a base slide from the source, as the import would, without its identification yet.
        sql(settings, "UPDATE slide SET origin = 'base', contributor_id = NULL WHERE short_id = :s", s=sid)
        sql(settings, "DELETE FROM identification")
        engine = make_sync_engine(database_path(settings))
        try:
            with engine.begin() as conn:
                assert store.backfill(conn) == {"slides": 1, "identifications": 1}
                assert store.backfill(conn) == {"slides": 1, "identifications": 0}  # idempotent
        finally:
            engine.dispose()
        listed = community(client, sid)["identifications"]
        assert len(listed) == 1 and listed[0]["source"] and listed[0]["by"] is None
