"""The bake: the base collection processed by the product's own pipeline into one declared output root.

``bake(out, vault)`` treats ``out`` as a complete Laminario data root: it creates the database there, stores every
validated lock slide as a published base-collection slide (the same ``create_slide`` a contribution goes through),
points each asset at its acquired file in the vault, queues the processing jobs (U4) and runs the worker until the
queue is empty, focal stacks fused on the way. Nothing is written outside ``out`` (R-073); the vault is only read.

``manifest.json`` in ``out`` lists every slide and asset row, the file behind every storage key with its SHA-256 and
size, and the taxon rows the slides use. The server imports that, and never re-bakes (``importer``).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import select, text

from app.base.acquire import load as load_acquired
from app.base.lock import LOCK, TAXA
from app.base.submission import source_path, submission
from app.collections.service import ResolvedAnchor
from app.config import Settings, get_settings
from app.contracts.ingest import validate_submission
from app.db.base import utcnow
from app.db.engine import async_sessions, make_async_engine, make_sync_engine
from app.db.migrate import upgrade_to_head
from app.db.models import Asset, Slide, Taxon
from app.jobs import queue
from app.services import slides as slide_service

INDEX = "bake-index.json"
MANIFEST = "manifest.json"
SLIDE_COLUMNS = [c.name for c in Slide.__table__.columns if c.name != "id"]
ASSET_COLUMNS = [c.name for c in Asset.__table__.columns if c.name not in ("id", "slide_id")]


def bake_settings(out: Path) -> Settings:
    here = get_settings()
    # Fusions of the large NMNH stacks run for hours on a workstation; the bake allows six.
    return Settings(data_root=out, vips_bin=here.vips_bin, public_base_url=here.public_base_url, fuse_timeout_s=21600)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolved(slide: dict) -> ResolvedAnchor:
    anchor = slide["specimen"]["anchor"]
    return ResolvedAnchor(anchor["ref"], anchor.get("rank"), anchor.get("classification"), facts=None)


async def _store(out: Path, slides: list[dict], acquired: dict, vault: Path, index: dict) -> list[int]:
    engine = make_async_engine(out / "laminario.sqlite3")
    created = []
    try:
        async with async_sessions(engine)() as db:
            known = {row.key for row in (await db.execute(select(Taxon))).scalars()}
            for t in json.loads(TAXA.read_text(encoding="utf-8")).values():
                if t["key"] not in known:
                    db.add(Taxon(key=t["key"], name=t["name"] or str(t["key"]), rank=t["rank"] or "",
                                 status=t["status"], accepted_key=t["accepted_key"],
                                 lineage_json=json.dumps(t["lineage"])))
            await db.commit()
            for slide in slides:
                if slide["id"] in index:
                    continue
                origins: list[dict] = []
                report = validate_submission(submission(slide, acquired, vault, origins=origins))
                if not report.valid:
                    raise ValueError(f"{slide['id']} does not validate: {report.errors[:2]}")
                row = await slide_service.create_slide(db, report.submission, resolved=_resolved(slide))
                row.status = "published"
                row.published_at = utcnow()
                for asset, origin in zip(row.assets, origins, strict=True):
                    asset.source_path = str(source_path(origin, acquired, vault))
                await db.commit()
                index[slide["id"]] = {"short_id": row.short_id, "digest": digest(slide)}
                created.append(row.id)
    finally:
        await engine.dispose()
    return created


def digest(slide: dict) -> str:
    """The lock entry's fingerprint: a baked slide whose entry changed since is baked again."""
    text_form = json.dumps(slide, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(text_form.encode("utf-8")).hexdigest()


def _stale(index: dict, slides: list[dict], refresh: set[str]) -> list[str]:
    """Baked slides to bake again: named in ``refresh``, or whose lock entry no longer has the recorded digest (an
    entry baked before digests were recorded is trusted unless named)."""
    by_id = {s["id"]: s for s in slides}
    stale = []
    for slide_id, entry in index.items():
        recorded = entry.get("digest") if isinstance(entry, dict) else None
        if slide_id in refresh or (slide_id in by_id and recorded and recorded != digest(by_id[slide_id])):
            stale.append(slide_id)
    return stale


def _remove(out: Path, index: dict, slide_ids: list[str]) -> None:
    """Take slides out of the bake root: their rows, jobs, journal and stored files."""
    settings = bake_settings(out)
    engine = make_sync_engine(out / "laminario.sqlite3")
    try:
        with engine.begin() as conn:
            for slide_id in slide_ids:
                entry = index.pop(slide_id)
                short_id = entry["short_id"] if isinstance(entry, dict) else entry
                row = conn.execute(text("SELECT id FROM slide WHERE short_id = :s"), {"s": short_id}).scalar()
                if row is None:
                    continue
                keys = conn.execute(text("SELECT storage_key FROM asset WHERE slide_id = :s "
                                         "AND storage_key IS NOT NULL"), {"s": row}).scalars().all()
                conn.execute(text("DELETE FROM job_event WHERE job_id IN (SELECT id FROM job WHERE slide_id = :s)"),
                             {"s": row})
                conn.execute(text("DELETE FROM job WHERE slide_id = :s"), {"s": row})
                conn.execute(text("DELETE FROM asset WHERE slide_id = :s"), {"s": row})
                conn.execute(text("DELETE FROM slide WHERE id = :s"), {"s": row})
                for key in keys:
                    (settings.store_root / key).unlink(missing_ok=True)
    finally:
        engine.dispose()


def _queue_processing(out: Path, slide_ids: list[int]) -> int:
    engine = make_sync_engine(out / "laminario.sqlite3")
    queued = 0
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT id, slide_id, plane_index, role FROM asset WHERE status = 'pending' "
                                     "AND slide_id IN (SELECT value FROM json_each(:ids))"),
                                {"ids": json.dumps(slide_ids)}).all()
        for asset_id, slide_id, plane_index, role in rows:
            payload = {"asset_id": asset_id}
            if role == "z_plane" and plane_index is not None:
                payload["plane"] = plane_index
            queue.enqueue(engine, "process_asset", payload, slide_id=slide_id)
            queued += 1
    finally:
        engine.dispose()
    return queued


def _run_worker(out: Path) -> int:
    from app.worker.runner import Worker

    engine = make_sync_engine(out / "laminario.sqlite3")
    done = 0
    try:
        while True:
            with engine.connect() as conn:
                waiting = conn.execute(text("SELECT COUNT(*) FROM job WHERE status = 'queued'")).scalar()
            if not waiting:
                return done
            done += Worker(bake_settings(out), name="base-bake").run(max_jobs=waiting)
    finally:
        engine.dispose()


def write_manifest(out: Path) -> dict:
    settings = bake_settings(out)
    engine = make_sync_engine(out / "laminario.sqlite3")
    slides_out = []
    try:
        with engine.connect() as conn:
            failed = conn.execute(text("SELECT COUNT(*) FROM job WHERE status = 'failed'")).scalar()
            for s in conn.execute(text("SELECT * FROM slide WHERE origin = 'base' ORDER BY id")).mappings():
                assets = []
                for a in conn.execute(text("SELECT * FROM asset WHERE slide_id = :s ORDER BY sort_order, id"),
                                      {"s": s["id"]}).mappings():
                    entry = {k: a[k] for k in ASSET_COLUMNS}
                    entry["source_path"] = None
                    if a["storage_key"]:
                        stored = settings.store_root / a["storage_key"]
                        entry["file"] = {"key": a["storage_key"], "sha256": _sha256(stored),
                                         "bytes": stored.stat().st_size}
                    assets.append(entry)
                slides_out.append({"slide": {k: s[k] for k in SLIDE_COLUMNS}, "assets": assets})
    finally:
        engine.dispose()
    taxa = json.loads(TAXA.read_text(encoding="utf-8"))
    manifest = {"about": "A Laminario base-collection bake: rows and stored files, imported by python -m app.base "
                         "import, never re-baked.", "baked_on": date.today().isoformat(),
                "failed_jobs": failed, "slides": slides_out, "taxa": list(taxa.values())}
    (out / MANIFEST).write_text(json.dumps(manifest, indent=1, ensure_ascii=False, default=str) + "\n",
                                encoding="utf-8")
    return manifest


def bake(out: Path, vault: Path, only: set[str] | None = None, refresh: set[str] | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    upgrade_to_head(out / "laminario.sqlite3")
    lock = yaml.safe_load(LOCK.read_text(encoding="utf-8"))
    chosen = [s for s in lock["slides"] if not only or s["id"] in only or s["collection"] in only]
    index_path = out / INDEX
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    # The bake root mirrors the lock: a slide the lock no longer holds leaves it with its files.
    gone = [slide_id for slide_id in index if slide_id not in {s["id"] for s in lock["slides"]}]
    if gone:
        _remove(out, index, gone)
        print(f"{len(gone)} slides are no longer in the lock and leave the bake: {', '.join(gone)}", flush=True)
    stale = _stale(index, lock["slides"], refresh or set())
    if stale:
        _remove(out, index, stale)
        index_path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
        print(f"{len(stale)} slides changed since they were baked and are baked again: {', '.join(stale)}", flush=True)
    created = asyncio.run(_store(out, chosen, load_acquired(), vault, index))
    index_path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    _queue_processing(out, created)
    _run_worker(out)
    return write_manifest(out)
