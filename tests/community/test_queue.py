"""R-1307: the Identify queue lists published slides that need identification, by collection and kind, oldest
first, and without the account's own when asked."""

from __future__ import annotations

from tests.accounts.support import app_client, settings_for

from .support import POLYPLAX_BOREALIS, identify, people, published, sql


def test_the_identify_queue(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        first = published(client, settings, p["maker"])
        second = published(client, settings, p["maker"])
        third = published(client, settings, p["maker"])
        sql(settings, "UPDATE slide SET published_at = '2026-01-0' || id WHERE short_id IN (:a, :b, :c)",
            a=first, b=second, c=third)

        queue = client.get("/api/identify").json()
        assert [s["id"] for s in queue["items"]] == [first, second, third] and queue["total"] == 3
        assert client.get("/api/identify?node=life.insects").json()["total"] == 3
        assert client.get("/api/identify?node=life.mammals").json()["total"] == 0
        assert client.get("/api/identify?kind=rock").json()["total"] == 0

        # Verified, it leaves the queue.
        identify(client, second, p["one"], POLYPLAX_BOREALIS)
        assert [s["id"] for s in client.get("/api/identify").json()["items"]] == [first, third]

        # Without the ones an account identified.
        identify(client, first, p["two"], {"kind": "taxon", "ref": "1032575", "name": "Polyplax alaskensis"})
        mine = client.get("/api/identify?unidentified_by_me=true", headers=p["two"]).json()
        assert [s["id"] for s in mine["items"]] == [third]
        assert client.get("/api/identify?badge=any").json()["total"] == 2
        # A reference slide appears only when asked for.
        sql(settings, "UPDATE asset SET pixel_size_um = NULL WHERE family = 'micro' AND slide_id = "
                      "(SELECT id FROM slide WHERE short_id = :s)", s=third)
        identify(client, third, p["three"], POLYPLAX_BOREALIS)
        assert client.get("/api/identify?badge=reference").json()["total"] == 1
