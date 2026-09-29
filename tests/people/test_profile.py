"""R-1401 to R-1403: an account's handle, its profile (never its email) and its cabinet of slides and identifications;
the slide record names its contributor by handle."""

from __future__ import annotations

from app.accounts.handles import slug
from tests.accounts.support import app_client, cli_invitation, register, settings_for, sign_in
from tests.community.support import POLYPLAX, POLYPLAX_BOREALIS, community, identify, people, published


def handle_of(client, headers: dict) -> str:
    return client.get("/api/session", headers=headers).json()["handle"]


def test_a_handle_is_the_display_name_made_plain():
    assert slug("Ana Pérez") == "ana-perez"
    assert slug("  María José  Ñúñez-Oyarzún ") == "maria-jose-nunez-oyarzun"
    assert slug("J. R. R. Tolkien") == "j-r-r-tolkien"
    assert slug("!!!") == "account" and slug("") == "account"
    assert len(slug("a" * 200)) == 60


def test_handles_are_unique(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        handles = []
        for email in ("one@example.org", "two@example.org", "three@example.org"):
            assert register(client, cli_invitation(settings, "contributor"), email, name="Ana Pérez").status_code == 201
            handles.append(handle_of(client, sign_in(client, email)))
        assert handles == ["ana-perez", "ana-perez-2", "ana-perez-3"]


def test_profile_counts_what_is_public(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        maker, one = handle_of(client, p["maker"]), handle_of(client, p["one"])
        first = published(client, settings, p["maker"])
        second = published(client, settings, p["maker"])
        # One agrees with the first slide (verified); two names only the genus on the second.
        assert identify(client, first, p["one"], POLYPLAX_BOREALIS).status_code == 201
        assert identify(client, second, p["two"], POLYPLAX, disagreement=True).status_code == 201
        assert community(client, first)["community"]["badge"] == "verified"

        answer = client.get(f"/api/people/{maker}")
        assert answer.status_code == 200, answer.text
        profile = answer.json()
        assert profile["handle"] == maker and profile["name"] == "Test Person" and profile["role"] == "contributor"
        assert profile["slides"] == 2 and profile["verified"] == 1
        assert profile["by_collection"] == {"life.insects": 2}
        assert profile["identifications"] == 0  # its own first identifications are not identifications of others'
        assert profile["last_active"] is not None
        assert "maker@example.org" not in answer.text and "email" not in profile

        theirs = client.get(f"/api/people/{one}").json()
        assert theirs["slides"] == 0 and theirs["identifications"] == 1
        assert theirs["categories"] == {"leading": 0, "improving": 0, "supporting": 1, "maverick": 0}
        two = client.get(f"/api/people/{handle_of(client, p['two'])}").json()
        assert two["identifications"] == 1 and sum(two["categories"].values()) == 1

        assert client.get("/api/people/nobody-at-all").status_code == 404

        # A hidden slide leaves the profile, and the identification on it with it.
        hid = client.post(f"/api/moderation/slide/{first}/hide", json={"reason": "Wrong specimen photographed"},
                          headers=p["curator"])
        assert hid.status_code == 204, hid.text
        assert client.get(f"/api/people/{maker}").json()["slides"] == 1
        assert client.get(f"/api/people/{one}").json()["identifications"] == 0


def test_the_cabinet_lists_slides_and_identifications(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        maker, one = handle_of(client, p["maker"]), handle_of(client, p["one"])
        sids = [published(client, settings, p["maker"]) for _ in range(3)]
        assert identify(client, sids[0], p["one"], POLYPLAX_BOREALIS).status_code == 201

        cabinet = client.get(f"/api/people/{maker}/slides").json()
        assert cabinet["total"] == 3 and sorted(s["id"] for s in cabinet["items"]) == sorted(sids)
        assert client.get(f"/api/people/{maker}/slides", params={"collection": "life.insects"}).json()["total"] == 3
        assert client.get(f"/api/people/{maker}/slides", params={"collection": "life.plants"}).json()["total"] == 0
        page = client.get(f"/api/people/{maker}/slides", params={"offset": 2, "limit": 2}).json()
        assert page["total"] == 3 and len(page["items"]) == 1
        assert client.get("/api/people/nobody-at-all/slides").status_code == 404

        idents = client.get(f"/api/people/{one}/identifications").json()
        assert len(idents) == 1
        assert idents[0]["slide"]["id"] == sids[0] and idents[0]["anchor"]["ref"] == "1032608"
        assert idents[0]["community"] is True and idents[0]["category"] == "supporting"
        assert client.get(f"/api/people/{maker}/identifications").json() == []

        # Each identification names its account's handle, the address of its cabinet.
        listed = {i["by_handle"] for i in community(client, sids[0])["identifications"]}
        assert listed == {maker, one}

        # The slide record names its contributor by handle, never by email.
        record = client.get(f"/api/slides/{sids[0]}")
        assert record.json()["contributor"] == {"handle": maker, "name": "Test Person"}
        assert "maker@example.org" not in record.text
