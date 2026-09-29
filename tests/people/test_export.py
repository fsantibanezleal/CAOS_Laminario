"""R-1407: an account exports its own slides, any status, with their exact places; no one else's."""

from __future__ import annotations

import csv
import io

from app.services.people import EXPORT_COLUMNS
from tests.accounts.support import app_client, settings_for
from tests.community.support import people, published


def rows_of(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def test_the_export_is_ones_own_with_exact_places(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"], geoprivacy="obscured")
        # The public record carries the obscured point, never the exact one.
        public = client.get(f"/api/slides/{sid}").json()["place"]
        assert public["geoprivacy"] == "obscured" and public["point"]["lat"] != -33.4489

        assert client.get("/api/people/me/slides.csv").status_code == 401
        answer = client.get("/api/people/me/slides.csv", headers=p["maker"])
        assert answer.status_code == 200 and answer.headers["content-type"].startswith("text/csv")
        assert answer.headers["cache-control"] == "no-store"
        assert "attachment" in answer.headers["content-disposition"]
        assert answer.text.splitlines()[0] == ",".join(EXPORT_COLUMNS)
        rows = rows_of(answer.text)
        assert [r["id"] for r in rows] == [sid]
        row = rows[0]
        assert row["status"] == "published" and row["geoprivacy"] == "obscured"
        assert float(row["latitude"]) == -33.4489 and float(row["longitude"]) == -70.6693
        assert row["anchor_ref"] == "1032608" and row["catalogue_number"] == "LAM-0001"
        assert row["permalink"].endswith(f"/s/{sid}") or sid in row["permalink"]

        # A draft is the account's too.
        from tests import payloads
        draft = client.post("/api/slide-cases", json=payloads.contribution(), headers=p["maker"])
        assert draft.status_code == 201
        rows = rows_of(client.get("/api/people/me/slides.csv", headers=p["maker"]).text)
        assert {r["status"] for r in rows} == {"published", "draft"}

        # Another account exports only its own (here, nothing).
        other = rows_of(client.get("/api/people/me/slides.csv", headers=p["one"]).text)
        assert other == []
