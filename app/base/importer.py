"""The import: a verified bake loaded into a Laminario database and slide store, without re-baking.

``import_bake(bake_root, settings)`` reads ``manifest.json``, checks every stored file of the bake against its SHA-256
and size, copies the files into the target store under the same storage keys (content addresses, so an identical file
is left in place), inserts the taxon rows the slides use, and inserts every slide and asset row as baked. A slide
whose short id is already in the target is refused when it is another slide; when it is the same base slide, its rows
are brought to the bake's if its record or its assets changed since (a country corrected, a slide baked again), and it
is skipped otherwise, so an import can be repeated. Nothing is processed: the bake did that.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from sqlalchemy import delete, insert, select, text, update

from app.community import store as community_store
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


def verify(bake_root: Path, manifest: dict, store: Path | None = None) -> list[str]:
    """Every stored file the manifest lists, checked against its SHA-256 and size in the bake's own store, or in
    ``store`` (the served store after an import); the problems found."""
    store = store if store is not None else bake_root / "store"
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


def manifest_files(manifest: dict) -> int:
    """How many stored files the manifest lists."""
    return sum(1 for entry in manifest["slides"] for asset in entry["assets"] if asset.get("file"))


#: Slide columns the import never takes from a bake: the community's (U13) and the curators'.
TARGET_ONLY = ("community_node", "community_rank", "badge", "hidden_from")

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


def _same(row, values: dict) -> bool:
    return all(getattr(row, k) == v for k, v in values.items() if k not in ("created_at", "updated_at", "published_at"))


def _refresh(conn, slide_id: int, slide: dict, assets: list[dict], slide_cols: set[str], asset_cols: set[str]) -> bool:
    """Bring a base slide already in the target to the bake's rows; whether anything changed."""
    values = _row(slide, slide_cols)
    current = conn.execute(select(Slide).where(Slide.id == slide_id)).first()
    if current.status == "hidden":
        values.pop("status", None)  # a curator's hiding stays until a curator restores the slide
    wanted = [_row(a, asset_cols) for a in assets]
    have = conn.execute(select(Asset).where(Asset.slide_id == slide_id).order_by(Asset.sort_order, Asset.id)).all()
    record_same = _same(current, values)
    assets_same = len(have) == len(wanted) and all(_same(h, w) for h, w in zip(have, wanted, strict=True))
    if not record_same:
        conn.execute(update(Slide).where(Slide.id == slide_id).values(**values))
    if not assets_same:
        conn.execute(delete(Asset).where(Asset.slide_id == slide_id))
        for w in wanted:
            conn.execute(insert(Asset).values(slide_id=slide_id, **w))
    return not (record_same and assets_same)


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
    # The community's and the curators' columns belong to the target, not to the bake (U13).
    slide_cols = {c.name for c in Slide.__table__.columns} - {"id", *TARGET_ONLY}
    asset_cols = {c.name for c in Asset.__table__.columns} - {"id", "slide_id"}
    copied = imported = updated = skipped = 0
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
                if existing is not None and existing.origin != "base":
                    raise ImportRefused(f"{slide['short_id']} is already another slide")
                for asset in entry["assets"]:
                    f = asset.get("file")
                    if f:
                        target = settings.store_root / f["key"]
                        if not (target.is_file() and target.stat().st_size == f["bytes"]
                                and _sha256(target) == f["sha256"]):
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(bake_root / "store" / f["key"], target)
                            copied += 1
                if existing is not None:
                    # A base slide is the bake's: a changed record or changed assets are brought over, the rest skipped.
                    if _refresh(conn, existing.id, slide, entry["assets"], slide_cols, asset_cols):
                        updated += 1
                        loaded.append(slide["short_id"])
                    else:
                        skipped += 1
                    continue
                slide_id = conn.execute(insert(Slide).values(**_row(slide, slide_cols))).inserted_primary_key[0]
                for asset in entry["assets"]:
                    conn.execute(insert(Asset).values(slide_id=slide_id, **_row(asset, asset_cols)))
                imported += 1
                loaded.append(slide["short_id"])
            # The search text is composed here, with the target's tree, not taken from the bake.
            search.reindex(conn, loaded)
            # The source's determination is the slide's first identification, and a changed one is recorded as
            # the source's new identification; the community and the badge follow (U13, R-1309).
            for sid in loaded:
                row = conn.execute(text("SELECT id, anchor_kind, anchor_ref, anchor_name, anchor_rank, "
                                        "anchor_classification FROM slide WHERE short_id = :s"), {"s": sid}).one()
                if not community_store.first_identification(conn, row.id):
                    community_store.source_determination(conn, row.id, row)
                community_store.refresh(conn, row.id)
    finally:
        engine.dispose()
    return {"imported": imported, "updated": updated, "skipped": skipped, "files_copied": copied}
