"""Countries: the vocabulary, the country a point lies in, and whether stated coordinates agree with a country."""

from __future__ import annotations

from sqlalchemy import text

from app.collections import places
from app.db.engine import database_path, make_sync_engine
from tests.accounts.support import account, app_client, settings_for
from tests.collections.test_api import case


def test_the_vocabulary_has_iso_codes_with_both_names():
    names = places.countries()
    assert len(names) == 257
    assert names["SB"] == {"en": "Solomon Islands", "es": "Islas Salomón"}
    assert names["FK"]["es"] == "Islas Malvinas"
    assert not {"EU", "UN", "ZZ", "QO"} & set(names)


def test_points_are_placed_in_their_country():
    assert places.locate(-33.4489, -70.6693) == "CL"  # Santiago
    assert places.locate(51.5074, -0.1278) == "GB"  # London: the four nations are one code
    assert places.locate(16.15, -61.68) == "GP"  # inland Basse-Terre: an overseas region has its own shape
    assert places.locate(16.2411, -61.5331) == "GP"  # Pointe-a-Pitre, on the channel: the nearest coast within reach
    assert places.locate(-9.4333, 159.95) == "SB"  # Honiara
    assert places.locate(-54.80, -68.30) == "AR"  # Ushuaia
    assert places.locate(0.0, -140.0) is None  # the open Pacific


def test_stated_countries_must_agree_with_coordinates():
    assert places.agrees("CL", -33.4489, -70.6693)
    assert not places.agrees("AR", -33.4489, -70.6693)
    assert places.agrees("CL", -33.03, -71.70)  # about 6 km off Valparaiso: within the coast's tolerance
    assert not places.agrees("CL", -33.0, -72.9)  # a degree out to sea
    assert places.agrees("GI", 36.14, -5.35)  # Gibraltar has no shape at 1:50m, so it cannot be checked


def test_submissions_state_or_imply_their_country(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        admin = account(client, settings, "admin", "admin@example.org")
        contributor = account(client, settings, "contributor", "c@example.org", issuer=admin)

        implied = client.post("/api/slide-cases", json=case(), headers=contributor)
        assert implied.status_code == 201

        stated = case()
        del stated["specimen"]["coordinates"]
        stated["specimen"]["country"] = "GP"
        assert client.post("/api/slide-cases", json=stated, headers=contributor).status_code == 201

        wrong = case(specimen__country="AR")
        refused = client.post("/api/slide-cases", json=wrong, headers=contributor)
        assert refused.status_code == 422
        error = refused.json()["errors"][0]
        assert error["field"] == "specimen.country" and error["message"].endswith("outside Argentina, in Chile")

        unknown = client.post("/api/slide-cases", json=case(specimen__country="QQ"), headers=contributor)
        assert unknown.status_code == 422 and unknown.json()["errors"][0]["field"] == "specimen.country"

        engine = make_sync_engine(database_path(settings))
        with engine.connect() as conn:
            rows = dict(conn.execute(text("SELECT short_id, country FROM slide")).all())
        engine.dispose()
        assert rows[implied.json()["id"]] == "CL"
        assert sorted(rows.values()) == ["CL", "GP"]
