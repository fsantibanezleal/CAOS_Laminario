"""The committed base collection (``data/base/lock.yaml``, ``acquired.json``, ``taxa.json``) against dossier 06.

These read the committed files only: the floors (R-070), the provenance of every asset (R-071), the polarised pairs
per rock family, and a sample of slides through the same offline checks ``python -m app.base validate`` runs. The
full validation writes the report; the sample here writes nothing outside the test's temporary folder.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date

import pytest
import yaml

from app.base.acquire import ACQUIRED
from app.base.lock import LOCK, TAXA
from app.base.validate import FLOORS, ROCK_FAMILIES, SHORTFALLS, check, collections
from app.contracts.licences import allowed


@pytest.fixture(scope="module")
def lock() -> dict:
    return yaml.safe_load(LOCK.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def acquired() -> dict:
    return json.loads(ACQUIRED.read_text(encoding="utf-8"))


def test_floors(lock: dict):
    slides = lock["slides"]
    per = Counter(s["collection"] for s in slides)
    assert len(slides) >= FLOORS["slides"]
    below = {c for c in collections() if per.get(c, 0) < FLOORS["per_collection"]}
    assert below <= set(SHORTFALLS), f"below the floor with no recorded reason: {sorted(below - set(SHORTFALLS))}"
    assert set(SHORTFALLS) <= below, "a recorded shortfall that is no longer short must be removed"
    assert all(per.get(c, 0) > 0 for c in collections()), "every collection holds at least one slide"
    wsi = sum(any(a.get("wsi") for a in s["assets"]) for s in slides)
    assert wsi >= FLOORS["wsi"]


def test_asset_provenance(lock: dict, acquired: dict):
    today = date.today().isoformat()
    for slide in lock["slides"]:
        assert slide["assets"], slide["id"]
        for asset in slide["assets"]:
            where = f"{slide['id']}: {asset['url']}"
            assert allowed(asset["licence"], "base"), where
            assert asset.get("creator") or asset.get("rights_holder"), where
            assert asset["record_url"].startswith("https://"), where
            assert 0 < len(asset["record_id"]) <= 200, where
            got = acquired.get(asset["url"])
            assert got is not None, f"{where} is not acquired"
            assert re.fullmatch(r"[0-9a-f]{64}", got["sha256"]), where
            assert got["file"].startswith(got["sha256"]), where
            assert got["retrieved_on"] <= today, where
            if asset.get("md5") or asset.get("sha256"):
                assert asset.get("wsi"), f"{where}: only whole-slide sources publish checksums"


def test_polarised_pairs(lock: dict):
    families = set()
    for slide in lock["slides"]:
        polarised = [a for a in slide["assets"] if a["role"] == "polarised"]
        if not polarised:
            continue
        states = sorted(a["polarisation"]["state"] for a in polarised)
        assert states == ["ppl", "xpl"], slide["id"]
        assert {a["modality"] for a in polarised} == {"polarised_ppl", "polarised_xpl"}, slide["id"]
        node = slide["placement"]["node"]
        if node.startswith("earth.rocks."):
            families.add(node.split(".")[2])
    assert set(ROCK_FAMILIES) <= families


def test_every_taxon_has_its_lineage(lock: dict):
    taxa = json.loads(TAXA.read_text(encoding="utf-8"))
    for slide in lock["slides"]:
        for anchor in (slide["specimen"]["anchor"], slide["specimen"].get("host")):
            if anchor and anchor["kind"] == "taxon":
                entry = taxa.get(anchor["ref"])
                # A kingdom has no ancestor: its lineage is empty, and itself is the whole path.
                assert entry is not None and (entry["lineage"] or entry["rank"] == "kingdom"), (
                    f"{slide['id']}: {anchor}")


def test_a_sample_passes_the_offline_checks(lock: dict, acquired: dict, tmp_path):
    # One plain (non-stack) slide per collection, through the contract and the tree without the network.
    sample, seen = [], set()
    for slide in lock["slides"]:
        if slide["collection"] not in seen and not any(a.get("stack") for a in slide["assets"]):
            seen.add(slide["collection"])
            sample.append(slide)
    results = check(sample, acquired, vault=None, workdir=tmp_path)
    failures = {r.slide_id: r.errors for r in results if r.errors}
    assert not failures
