"""R-1304: the badge from the slide checks and the community, the vote "as good as it can be", and the votes cleared
when the community anchor changes."""

from __future__ import annotations

import pytest

from app.community.quality import badge
from tests.accounts.support import app_client, settings_for

from .support import POLYPLACIDAE, POLYPLAX, POLYPLAX_ALASKENSIS, community, identify, people, published, sql

SPECIES, GENUS, FAMILY = "taxon:1032608", "taxon:1032563", "taxon:4369"


@pytest.mark.parametrize(("checks", "node", "rank", "votes", "expected"), [
    (False, SPECIES, "species", (0, 0), "reference"),      # a failed check decides
    (True, None, None, (0, 0), "needs_id"),                # no community anchor yet
    (True, SPECIES, "species", (0, 0), "verified"),        # a species is as fine as a taxon needs
    (True, SPECIES, "species", (0, 1), "needs_id"),        # the community says it still needs identification
    (True, GENUS, "genus", (0, 0), "needs_id"),            # a genus is not enough on its own
    (True, GENUS, "genus", (2, 1), "verified"),            # voted as good as it can be, below a family
    (True, FAMILY, "family", (2, 0), "reference"),         # voted, but a family is too coarse
    (True, "rock:igneous.coarse/granite", None, (0, 0), "verified"),
    (True, "rock:igneous.coarse", None, (0, 0), "needs_id"),
    (True, "rock:igneous.coarse", None, (1, 0), "reference"),  # a rock family never verifies
    (True, "mineral:9.A.C.05/forsterite", "species", (0, 0), "verified"),
    (True, "mineral:9.A.C.05", "group", (1, 0), "verified"),   # a mineral group, voted
    (True, "crystal:ice.P", None, (0, 0), "verified"),
    (True, "crystal:ice", None, (1, 0), "verified"),
    (True, "material:fibre/cotton", None, (0, 0), "verified"),
])
def test_badge_rule(checks, node, rank, votes, expected):
    assert badge(checks, node, rank, *votes) == expected


def test_votes_decide_and_are_cleared_when_the_anchor_changes(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"])
        identify(client, sid, p["one"], POLYPLAX_ALASKENSIS)  # one against one: the genus
        result = community(client, sid, p["one"])["community"]
        assert (result["node"], result["badge"]) == (GENUS, "needs_id")

        assert client.put(f"/api/slides/{sid}/vote", json={"as_good_as_it_can_be": True},
                          headers=p["maker"]).status_code == 403  # a contributor does not vote
        assert client.put(f"/api/slides/{sid}/vote", json={"as_good_as_it_can_be": True},
                          headers=p["one"]).status_code == 204
        result = community(client, sid, p["one"])["community"]
        assert (result["badge"], result["as_good_as_it_can_be"], result["my_vote"]) == ("verified", 1, True)
        assert client.put(f"/api/slides/{sid}/vote", json={"as_good_as_it_can_be": False},
                          headers=p["two"]).status_code == 204
        assert community(client, sid)["community"]["badge"] == "needs_id"  # one each: it still needs identification

        # A new community anchor clears the votes (R-1304): three of four now name P. alaskensis.
        identify(client, sid, p["two"], POLYPLAX_ALASKENSIS)
        identify(client, sid, p["three"], POLYPLAX_ALASKENSIS, body="The paratergal plates")
        result = community(client, sid)["community"]
        assert result["node"] == "taxon:1032575"
        assert (result["as_good_as_it_can_be"], result["needs_more"]) == (0, 0)
        assert sql(settings, "SELECT COUNT(*) AS n FROM slide_vote")[0].n == 0

        # A family voted as good as it can be is a reference slide.
        coarse = published(client, settings, p["maker"])
        identify(client, coarse, p["one"], POLYPLACIDAE, disagreement=True)
        identify(client, coarse, p["two"], POLYPLACIDAE, disagreement=True)
        assert community(client, coarse)["community"]["node"] == FAMILY
        client.put(f"/api/slides/{coarse}/vote", json={"as_good_as_it_can_be": True}, headers=p["one"])
        assert community(client, coarse)["community"]["badge"] == "reference"
        # Taking the vote back returns it to needs ID.
        client.put(f"/api/slides/{coarse}/vote", json={"as_good_as_it_can_be": None}, headers=p["one"])
        assert community(client, coarse)["community"]["badge"] == "needs_id"
        assert POLYPLAX["rank"] == "genus"


def test_a_fused_composite_is_not_a_missing_source():
    """A base focal stack's composites and height map carry the licence and no source of their own: the slide's
    licence-and-provenance check reads its originals (found on the NMNH stacks of the base collection)."""
    from types import SimpleNamespace as Row

    from app.services.catalog import quality_checks

    by = "https://creativecommons.org/licenses/by/4.0/"
    plane = Row(family="micro", role="z_plane", licence_uri=by, source_url="https://zenodo.org/r/1/f.ndpi",
                pixel_size_um=0.23, modality="brightfield")
    fused = [Row(family="micro", role=r, licence_uri=by, source_url=None, pixel_size_um=0.23, modality="brightfield")
             for r in ("edf_wavelet", "edf_variance", "height_map")]
    photo = Row(family="macro", role="slide_overview", licence_uri=by, source_url="https://zenodo.org/r/1/m.jpg",
                pixel_size_um=None, modality=None)
    checks = {c.code: c for c in quality_checks("base", [plane, *fused, photo])}
    assert checks["licence_and_provenance"].passed
    unsourced = Row(family="micro", role="single", licence_uri=by, source_url=None, pixel_size_um=0.5,
                    modality="brightfield")
    checks = {c.code: c for c in quality_checks("base", [plane, unsourced, photo])}
    assert not checks["licence_and_provenance"].passed
