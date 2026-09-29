"""R-1303: when the community anchor changes, the slide takes it and the tree places it again, keeping a drawer that
still accepts it and a curator's override."""

from __future__ import annotations

from tests.accounts.support import app_client, settings_for

from .support import HOMO_SAPIENS, POLYPLAX_ALASKENSIS, community, identify, people, published, sql


def slide_row(settings, sid):
    return sql(settings, "SELECT anchor_ref, anchor_name, anchor_rank, placement_node, community_node, "
                         "search_text FROM slide WHERE short_id = :s", s=sid)[0]


def test_the_slide_follows_the_community(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"])  # Polyplax borealis, in life.insects.lice

        # Two say P. alaskensis against the contributor's P. borealis: the species scores 2/3, the genus agrees.
        identify(client, sid, p["one"], POLYPLAX_ALASKENSIS)
        identify(client, sid, p["two"], POLYPLAX_ALASKENSIS)
        row = slide_row(settings, sid)
        assert (row.community_node, row.anchor_ref, row.anchor_rank) == ("taxon:1032563", "1032563", "genus")
        assert row.placement_node == "life.insects.lice"  # the drawer still accepts the genus
        assert "Polyplax" in row.search_text

        # A third: 3 of 4 for P. alaskensis, above two thirds; the slide takes the species.
        identify(client, sid, p["three"], POLYPLAX_ALASKENSIS)
        row = slide_row(settings, sid)
        assert (row.community_node, row.anchor_ref, row.anchor_name) == (
            "taxon:1032575", "1032575", "Polyplax alaskensis")
        assert community(client, sid)["community"]["anchor"]["name"] == "Polyplax alaskensis"
        assert client.get("/api/slides?q=alaskensis").json()["total"] == 1


def test_a_new_anchor_the_drawer_refuses_moves_the_slide(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"], host=None)
        for who in ("one", "two", "three"):
            assert identify(client, sid, p[who], HOMO_SAPIENS).status_code == 201
        row = slide_row(settings, sid)
        assert row.anchor_ref == "2436436"
        assert row.placement_node.startswith("life.mammals"), row.placement_node

        # A curator's placement override is kept whatever the community says.
        other = published(client, settings, p["maker"], host=None)
        sql(settings, "UPDATE slide SET placement_override_reason = 'kept here on purpose' WHERE short_id = :s",
            s=other)
        for who in ("one", "two", "three"):
            identify(client, other, p[who], HOMO_SAPIENS)
        row = slide_row(settings, other)
        assert row.anchor_ref == "2436436" and row.placement_node == "life.insects.lice"
