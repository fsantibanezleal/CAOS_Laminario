"""R-1009: a base slide carries a country only where its source states one, and a change of its record reaches the
bake and the import without processing its images again.

The committed lock is checked offline: every country is a code of the vocabulary and comes with the locality or the
NHM record that states it. The bake's two fingerprints are checked on lock entries, and a sandboxed bake of two small
slides (vault and libvips, skipped otherwise) gains a country and a new credit line with no processing job queued, then
the import updates the served rows.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.base import bake as bake_module
from app.base.bake import _stale, digest, pixels_digest
from app.base.lock import LOCK
from app.collections import places


@pytest.fixture(scope="module")
def lock() -> dict:
    return yaml.safe_load(LOCK.read_text(encoding="utf-8"))


def _nhm(slide: dict) -> bool:
    return any("nhm.ac.uk" in a["record_url"] for a in slide["assets"])


def test_countries_are_stated(lock: dict):
    placed = [s for s in lock["slides"] if s["specimen"].get("country")]
    # Dossier 12: the NHM occurrences, the NMNH sheets and the localities transcribed from the sources.
    assert len(placed) >= 69
    for slide in placed:
        code = slide["specimen"]["country"]
        assert places.known(code), (slide["id"], code)
        # Stated by the source: a transcribed locality, or the NHM record's own country.
        assert slide["specimen"].get("locality_text") or _nhm(slide), slide["id"]
    # Nothing without a stated place was given a country.
    unplaced = [s for s in lock["slides"] if not s["specimen"].get("country")]
    assert all(not s["specimen"].get("locality_text") or not places.code_of(s["specimen"]["locality_text"])
               for s in unplaced)


def test_country_names_map_to_codes():
    assert places.code_of("Solomon Islands") == "SB"
    assert places.code_of("falkland islands") == "FK"
    assert places.code_of("Guadalupe") == "GP"  # the Spanish name
    assert places.code_of("Kidney Isle") is None  # a place is not a country


def test_a_record_change_keeps_the_images():
    slide = {"id": "x", "specimen": {"anchor": {"name": "Granite"}},
             "assets": [{"url": "https://a", "role": "single", "licence": "CC-BY-4.0", "creator": "Unknown"}]}
    index = {"x": {"short_id": "AAAAAAAA", "digest": digest(slide), "pixels": pixels_digest(slide)}}
    placed = {**slide, "specimen": {**slide["specimen"], "country": "GB"}}
    assert _stale(index, [placed], set()) == ([], ["x"])  # the record changed, the images did not
    credited = {**slide, "assets": [{**slide["assets"][0], "creator": "A. Collector", "licence": "CC0-1.0"}]}
    assert _stale(index, [credited], set()) == ([], ["x"])  # so did a credit line and a licence
    moved = {**slide, "assets": [{**slide["assets"][0], "url": "https://b"}]}
    assert _stale(index, [moved], set()) == (["x"], [])  # new images: baked again
    assert _stale(index, [slide], {"x"}) == (["x"], [])  # named: baked again
    legacy = {"x": {"short_id": "AAAAAAAA", "digest": digest(slide)}}
    assert _stale(legacy, [placed], set()) == (["x"], [])  # no pixels fingerprint, not upgraded: baked again


def test_a_country_reaches_the_bake_and_the_import_without_processing(fixtures: Path, vips, tmp_path: Path,
                                                                      monkeypatch, lock: dict):
    from app.imaging.library import info

    if not info().openslide:
        pytest.skip("libvips with OpenSlide is not available")
    from tests.base.test_bake_sandbox import _small_slides

    vault = fixtures / "base"
    chosen = [i for i in _small_slides(vault, 6)
              if not next(s for s in lock["slides"] if s["id"] == i)["specimen"].get("country")][:2]
    if len(chosen) < 2:
        pytest.skip("the vault holds no acquired base sources without a country")

    from sqlalchemy import text

    from app.base.importer import import_bake
    from app.config import Settings
    from app.db.engine import make_sync_engine

    out = tmp_path / "bake"
    bake_module.bake(out, vault, only=set(chosen))
    target = Settings(data_root=tmp_path / "server")
    assert import_bake(out, target)["imported"] == 2

    # The lock gains a country and a new credit line for both slides (a copy, never the committed file).
    changed = yaml.safe_load(LOCK.read_text(encoding="utf-8"))
    for s in changed["slides"]:
        if s["id"] in chosen:
            s["specimen"]["country"] = "GP"
            for a in s["assets"]:
                a["creator"] = "A credit rewritten in the lock"
    patched = tmp_path / "lock.yaml"
    patched.write_text(yaml.safe_dump(changed, sort_keys=False, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(bake_module, "LOCK", patched)

    def jobs() -> int:
        engine = make_sync_engine(out / "laminario.sqlite3")
        with engine.connect() as conn:
            n = conn.execute(text("SELECT COUNT(*) FROM job")).scalar_one()
        engine.dispose()
        return n

    before = jobs()
    bake_module.bake(out, vault, only=set(chosen))
    assert jobs() == before, "a record change queued processing"
    index = json.loads((out / bake_module.INDEX).read_text(encoding="utf-8"))
    assert all(index[i]["digest"] == digest(next(s for s in changed["slides"] if s["id"] == i)) for i in chosen)
    engine = make_sync_engine(out / "laminario.sqlite3")
    try:
        with engine.connect() as conn:
            creators = set(conn.execute(text("SELECT creator FROM asset")).scalars())
    finally:
        engine.dispose()
    assert creators == {"A credit rewritten in the lock"}, creators

    # An index made before the pixels fingerprint (plain short ids) is judged by the stored images: the same
    # files, so nothing is processed and the records stay as the lock has them.
    (out / bake_module.INDEX).write_text(json.dumps({i: index[i]["short_id"] for i in chosen}), encoding="utf-8")
    bake_module.bake(out, vault, only=set(chosen))
    assert jobs() == before, "an old index entry with unchanged files queued processing"
    upgraded = json.loads((out / bake_module.INDEX).read_text(encoding="utf-8"))
    assert all(upgraded[i]["short_id"] == index[i]["short_id"] and upgraded[i]["pixels"] for i in chosen)

    result = import_bake(out, target)
    assert result["updated"] == 2 and result["imported"] == 0
    engine = make_sync_engine(target.data_root / "laminario.sqlite3")
    try:
        with engine.connect() as conn:
            countries = conn.execute(text("SELECT country FROM slide")).scalars().all()
            found = conn.execute(text("SELECT COUNT(*) FROM slide_search WHERE slide_search MATCH :q"),
                                 {"q": '"guadalupe"'}).scalar_one()
    finally:
        engine.dispose()
    assert countries == ["GP", "GP"] and found == 2
    engine = make_sync_engine(target.data_root / "laminario.sqlite3")
    try:
        with engine.connect() as conn:
            served = set(conn.execute(text("SELECT creator FROM asset")).scalars())
    finally:
        engine.dispose()
    assert served == {"A credit rewritten in the lock"}, served
    assert import_bake(out, target)["skipped"] == 2  # nothing changed since: repeated, it does nothing
