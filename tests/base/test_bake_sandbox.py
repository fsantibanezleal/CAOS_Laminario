"""The bake writes only into its declared output root, and its import is verified (R-073).

Two small slides of the committed lock are baked from the data vault into the test's temporary folder with the
product's own pipeline, then imported into a second temporary deployment; the canonical files of the repository
(the lock, the acquisition record, the taxa, the report) must be byte-identical before and after. Runs locally with
the vault (``LAMINARIO_FIXTURES``) and libvips; skipped otherwise.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from app.base.acquire import ACQUIRED
from app.base.lock import LOCK, SELECTION, TAXA
from app.base.validate import REPORT

CANONICAL = [LOCK, SELECTION, TAXA, ACQUIRED, REPORT]


def _digest(paths: list[Path]) -> dict[str, str | None]:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None for p in paths}


def _small_slides(vault: Path, count: int = 2) -> list[str]:
    lock = yaml.safe_load(LOCK.read_text(encoding="utf-8"))
    acquired = json.loads(ACQUIRED.read_text(encoding="utf-8"))
    chosen = []
    for slide in lock["slides"]:
        urls = [a["url"] for a in slide["assets"]]
        if any(a.get("wsi") for a in slide["assets"]) or not all(u in acquired for u in urls):
            continue
        files = [vault / "sources" / acquired[u]["file"] for u in urls]
        if all(f.exists() and f.stat().st_size < 3_000_000 for f in files):
            chosen.append(slide["id"])
        if len(chosen) == count:
            break
    return chosen


def test_tests_never_write_canonical_outputs(fixtures: Path, vips, tmp_path: Path):
    from app.imaging.library import info

    if not info().openslide:
        pytest.skip("libvips with OpenSlide is not available")
    vault = fixtures / "base"
    chosen = _small_slides(vault)
    if len(chosen) < 2:
        pytest.skip("the vault holds no acquired base sources")
    before = _digest(CANONICAL)

    from app.base.bake import MANIFEST, bake
    from app.base.importer import import_bake
    from app.config import Settings

    out = tmp_path / "bake"
    manifest = bake(out, vault, only=set(chosen))
    assert manifest["failed_jobs"] == 0
    assert {s["slide"]["origin"] for s in manifest["slides"]} == {"base"}
    assert len(manifest["slides"]) == 2
    assert all(a.get("file") for s in manifest["slides"] for a in s["assets"])
    assert (out / MANIFEST).exists()

    target = Settings(data_root=tmp_path / "server")
    first = import_bake(out, target)
    again = import_bake(out, target)
    assert first["imported"] == 2 and again["imported"] == 0 and again["skipped"] == 2

    # The imported slides are found by search: their text is composed at import, with the target's tree.
    from sqlalchemy import text

    from app.db.engine import make_sync_engine

    engine = make_sync_engine(target.data_root / "laminario.sqlite3")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT short_id, anchor_name, search_text FROM slide")).all()
            assert len(rows) == 2 and all(r.search_text for r in rows)
            for short_id, anchor_name, _ in rows:
                for term in (short_id, anchor_name.split()[0]):
                    hits = conn.execute(text("SELECT s.short_id FROM slide_search JOIN slide s "
                                             "ON s.id = slide_search.rowid WHERE slide_search MATCH :q"),
                                        {"q": f'"{term}"'}).scalars().all()
                    assert short_id in hits, (short_id, term)
    finally:
        engine.dispose()

    assert _digest(CANONICAL) == before
    written = [p for p in Path(LOCK).parent.rglob("*") if p.is_file() and p.stat().st_mtime > out.stat().st_ctime]
    assert not written, f"the bake wrote into the repository: {written}"
