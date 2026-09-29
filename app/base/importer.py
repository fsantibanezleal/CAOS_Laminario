"""The import: a verified bake loaded into a Laminario database and slide store, without re-baking.

``import_bake(bake_root, settings)`` reads ``manifest.json``, checks every stored file of the bake against its SHA-256
and size, copies the files into the target store under the same storage keys (content addresses, so an identical file
is left in place), inserts the taxon rows the slides use, and inserts every slide and asset row as baked. A slide
whose short id is already in the target is skipped when it is the same base slide (so an import can be repeated) and
refused when it is another slide. Nothing is processed: the bake did that.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from sqlalchemy import insert, select

from app.config import Settings
from app.db.engine import make_sync_engine
from app.db.migrate import upgrade_to_head
from app.db.models import Asset, Slide, Taxon
from app.services import search

MANIFEST = "manifest.json"


class ImportRefused(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(bake_root: Path, manifest: dict) -> list[str]:
    """Every stored file of the bake, checked against the manifest; the problems found."""
    store = bake_root / "store"
    problems = []
    for entry in manifest["slides"]:
        for asset in entry["assets"]:
            f = asset.get("file")
            if not f:
                continue
            path = store / f["key"]
            if not path.is_file():
                problems.append(f"{f['key']}: missing")
            elif path.stat().st_size != f["bytes"] or _sha256(path) != f["sha256"]:
                problems.append(f"{f['key']}: differs from the manifest")
    return problems


def _row(values: dict, columns: set[str]) -> dict:
    from datetime import date, datetime

    out = {}
    for k, v in values.items():
        if k not in columns:
            continue
        if k in ("created_at", "updated_at", "published_at", "fetched_at") and isinstance(v, str):
            v = datetime.fromisoformat(v)
        if k == "source_retrieved_on" and isinstance(v, str):
            v = date.fromisoformat(v)
        out[k] = v
    return out


def import_bake(bake_root: Path, settings: Settings) -> dict:
    manifest = json.loads((bake_root / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("failed_jobs"):
        raise ImportRefused(f"the bake has {manifest['failed_jobs']} failed jobs")
    problems = verify(bake_root, manifest)
    if problems:
        raise ImportRefused("; ".join(problems[:5]))
    database = settings.data_root / "laminario.sqlite3"
    upgrade_to_head(database)
    engine = make_sync_engine(database)
    slide_cols = {c.name for c in Slide.__table__.columns} - {"id"}
    asset_cols = {c.name for c in Asset.__table__.columns} - {"id", "slide_id"}
    copied = imported = skipped = 0
    loaded: list[str] = []
    try:
        with engine.begin() as conn:
            known_taxa = set(conn.execute(select(Taxon.key)).scalars())
            for t in manifest["taxa"]:
                if t["key"] not in known_taxa:
                    conn.execute(insert(Taxon).values(key=t["key"], name=t["name"] or str(t["key"]),
                                                      rank=t["rank"] or "", status=t["status"],
                                                      accepted_key=t["accepted_key"],
                                                      lineage_json=json.dumps(t["lineage"])))
            for entry in manifest["slides"]:
                slide = entry["slide"]
                existing = conn.execute(select(Slide.id, Slide.origin).where(
                    Slide.short_id == slide["short_id"])).first()
                if existing is not None:
                    if existing.origin != "base":
                        raise ImportRefused(f"{slide['short_id']} is already another slide")
                    skipped += 1
                    continue
                for asset in entry["assets"]:
                    f = asset.get("file")
                    if f:
                        target = settings.store_root / f["key"]
                        if not (target.is_file() and target.stat().st_size == f["bytes"]
                                and _sha256(target) == f["sha256"]):
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(bake_root / "store" / f["key"], target)
                            copied += 1
                slide_id = conn.execute(insert(Slide).values(**_row(slide, slide_cols))).inserted_primary_key[0]
                for asset in entry["assets"]:
                    conn.execute(insert(Asset).values(slide_id=slide_id, **_row(asset, asset_cols)))
                imported += 1
                loaded.append(slide["short_id"])
            # The search text is composed here, with the target's tree, not taken from the bake.
            search.reindex(conn, loaded)
    finally:
        engine.dispose()
    return {"imported": imported, "skipped": skipped, "files_copied": copied}
