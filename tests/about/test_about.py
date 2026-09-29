"""R-1501, R-1502, R-1507: the About answer counts the collection as the database holds it, knows every source and
licence its images carry, and names the credits (``app/about/credits.json``)."""

from __future__ import annotations

from urllib.parse import urlparse

import yaml

from app.base.lock import LOCK
from app.contracts import licences
from app.services import about
from tests.accounts.support import app_client, settings_for
from tests.community.support import POLYPLAX_BOREALIS, identify, people, published, sql

COMMONS_FILE = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Polyplax.jpg"
BY_SA_3 = "https://creativecommons.org/licenses/by-sa/3.0/"


def test_the_numbers_and_the_counts(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        empty = client.get("/api/about")
        assert empty.status_code == 200 and empty.json()["numbers"]["slides"] == 0
        assert empty.headers["cache-control"] == "public, max-age=60"

        p = people(client, settings)
        own, other, hidden = (published(client, settings, p["maker"]) for _ in range(3))
        # One becomes a base slide from Commons under CC BY-SA 3.0, as the import would make it.
        sql(settings, "UPDATE slide SET origin = 'base', contributor_id = NULL WHERE short_id = :s", s=other)
        # A base slide's first identification is the source's, never an account's.
        sql(settings, "UPDATE identification SET user_id = NULL WHERE slide_id = "
                      "(SELECT id FROM slide WHERE short_id = :s)", s=other)
        sql(settings, "UPDATE asset SET source_url = :u, licence_uri = :l WHERE slide_id = "
                      "(SELECT id FROM slide WHERE short_id = :s)", u=COMMONS_FILE, l=BY_SA_3, s=other)
        # A composite fused from a stack is not an image of its own.
        sql(settings, "UPDATE asset SET role = 'edf_wavelet' WHERE id = (SELECT MIN(a.id) FROM asset a JOIN slide s "
                      "ON s.id = a.slide_id WHERE s.short_id = :s AND a.family = 'micro')", s=own)
        hid = client.post(f"/api/moderation/slide/{hidden}/hide", json={"reason": "Wrong specimen photographed"},
                          headers=p["curator"])
        assert hid.status_code == 204
        assert identify(client, own, p["one"], POLYPLAX_BOREALIS).status_code == 201

        answer = client.get("/api/about").json()
        numbers = answer["numbers"]
        assert numbers["slides"] == 2 and numbers["by_origin"] == {"base": 1, "contribution": 1}
        assert numbers["realms"] == [{"id": "life", "slides": 2, "collections": {"life.insects": 2}}]
        assert numbers["images"] == 3  # two per slide, less the composite
        assert numbers["contributors"] == 1 and numbers["countries"] == 1
        # The community's work: the identifier's, not the contributor's own first identification.
        assert numbers["identifications"] == 1

        sources = {s["id"]: s for s in answer["sources"]}
        assert set(sources) == {"commons", "contribution"}
        assert sources["commons"]["slides"] == 1 and sources["commons"]["images"] == 2
        assert sources["commons"]["licences"] == {BY_SA_3: 2}
        assert sources["commons"]["name"] == "Wikimedia Commons"
        assert sources["contribution"]["images"] == 1
        licence_rows = {row["uri"]: row for row in answer["licences"]}
        assert licence_rows[BY_SA_3]["short"] == "CC BY-SA 3.0" and licence_rows[BY_SA_3]["family"] == "by-sa"
        assert sum(row["images"] for row in answer["licences"]) == numbers["images"]
        assert answer["policy"]["base"] == ["cc0", "pdm", "nkc", "by", "by-sa"]

        # R-1507: the credits, each with its address; a licence where the source states one.
        for group in ("vocabularies", "map", "software", "fonts"):
            assert answer[group] and all(item["url"].startswith("https://") for item in answer[group])
        vocabularies = {v["id"]: v for v in answer["vocabularies"]}
        assert vocabularies["gbif"]["doi"] == "10.15468/39omei"
        assert vocabularies["kikuchi"]["doi"] == "10.1016/j.atmosres.2013.06.006"


def test_every_source_of_the_base_collection_is_known():
    """A base image from a host no source claims would be counted as 'other', with no words on the About page."""
    lock = yaml.safe_load(LOCK.read_text(encoding="utf-8"))
    hosts = {urlparse(a["url"]).netloc for s in lock["slides"] for a in s["assets"]}
    unknown = sorted(h for h in hosts if about.source_of(f"https://{h}/x", "base") == about.OTHER)
    assert unknown == []
    ids = [s["id"] for s in about.credits()["sources"]]
    assert len(ids) == len(set(ids))


def test_every_licence_family_is_one_the_policy_names():
    lock = yaml.safe_load(LOCK.read_text(encoding="utf-8"))
    families = {about.family(a["licence"]) for s in lock["slides"] for a in s["assets"]}
    assert families <= set(about.POLICY["base"])
    assert about.family(licences.CC0) == "cc0" and about.family(licences.PDM) == "pdm"
    assert about.family("https://creativecommons.org/licenses/by-nc/4.0/") == "by-nc"
    assert set(about.POLICY["base"]) < set(about.POLICY["contribution"])
