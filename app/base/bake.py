"""The bake: the base collection processed by the product's own pipeline into one declared output root.

``bake(out, vault)`` treats ``out`` as a complete Laminario data root: it creates the database there, stores every
validated lock slide as a published base-collection slide (the same ``create_slide`` a contribution goes through),
points each asset at its acquired file in the vault, queues the processing jobs (U4) and runs the worker until the
queue is empty, focal stacks fused on the way. Nothing is written outside ``out`` (R-073); the vault is only read.

``manifest.json`` in ``out`` lists every slide and asset row, the file behind every storage key with its SHA-256 and
size, and the taxon rows the slides use. The server imports that, and never re-bakes (``importer``).

The bake index records two fingerprints of each baked lock entry: of its pixels (its assets without their credits:
what the images are made from) and of the whole entry. A slide whose pixels changed is baked again; a slide whose
record alone changed (a country, a locality, a determination, a licence or a credit line) has its rows rewritten in
place, images kept, so correcting a label never fuses a focal stack again. An index entry made before the pixels
fingerprint is upgraded from the bake's own rows: if its stored images come from exactly the files the lock now names
(source address and SHA-256), only its record is rewritten; otherwise it is baked again.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
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
from app.services.catalog import DERIVED_ROLES

INDEX = "bake-index.json"
MANIFEST = "manifest.json"
SLIDE_COLUMNS = [c.name for c in Slide.__table__.columns if c.name != "id"]
ASSET_COLUMNS = [c.name for c in Asset.__table__.columns if c.name not in ("id", "slide_id")]
#: Lock asset fields that credit or describe an image without changing its pixels.
CREDIT_FIELDS = ("licence", "rights_holder", "creator", "caption", "record_id", "record_url")
#: The asset columns a record refresh rewrites on a stored image (the credit fields, as the submission maps them).
ASSET_CREDIT_COLUMNS = ("licence_uri", "rights_holder", "creator", "caption", "source_record_id")


def bake_settings(out: Path) -> Settings:
    here = get_settings()
    # Fusions of the large NMNH stacks run for hours on a workstation; the bake allows six.
    # The bake runs on a workstation: a stack's windows fuse in as many processes as leave four cores free, at most
    # twelve (a window of eleven colour planes needs about half a gigabyte).
    workers = max(1, min(12, (os.cpu_count() or 1) - 4))
    return Settings(data_root=out, vips_bin=here.vips_bin, public_base_url=here.public_base_url, fuse_timeout_s=21600,
                    fuse_workers=workers)


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
                index[slide["id"]] = {"short_id": row.short_id, "digest": digest(slide),
                                      "pixels": pixels_digest(slide)}
                created.append(row.id)
    finally:
        await engine.dispose()
    return created


def _fingerprint(value) -> str:
    text_form = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(text_form.encode("utf-8")).hexdigest()


def digest(slide: dict) -> str:
    """The whole lock entry's fingerprint."""
    return _fingerprint(slide)


def pixels_digest(slide: dict) -> str:
    """The fingerprint of what a slide's images are made from: its assets without their credits (files, roles, planes,
    policies, sizes, modalities)."""
    return _fingerprint([{k: v for k, v in a.items() if k not in CREDIT_FIELDS} for a in slide.get("assets", [])])


def _short_id(entry) -> str:
    return entry["short_id"] if isinstance(entry, dict) else entry


def lock_files(slide: dict, acquired: dict) -> set[tuple[str, str | None]]:
    """The source files a lock entry names: (address, SHA-256 of the retrieved bytes)."""
    return {(a["url"], acquired.get(a["url"], {}).get("sha256")) for a in slide.get("assets", [])}


def baked_files(out: Path) -> dict[str, set[tuple[str, str | None]]]:
    """The source files the stored images of each baked slide come from, by short id (derived images excluded)."""
    engine = make_sync_engine(out / "laminario.sqlite3")
    files: dict[str, set] = {}
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT s.short_id, a.source_url, a.source_sha256 FROM asset a JOIN slide s ON s.id = a.slide_id "
                "WHERE a.source_url IS NOT NULL AND a.role NOT IN (SELECT value FROM json_each(:derived))"),
                {"derived": json.dumps(DERIVED_ROLES)}).all()
    finally:
        engine.dispose()
    for short_id, url, sha in rows:
        files.setdefault(short_id, set()).add((url, sha))
    return files


def upgrade_entries(index: dict, slides: list[dict], baked: dict[str, set], acquired: dict) -> tuple[int, int]:
    """Give every index entry made before the pixels fingerprint one, judged by the bake's own rows (``baked``, from
    ``baked_files``): an entry whose stored images come from exactly the files its lock entry now names gains the
    current pixels fingerprint, so only its record is rewritten; any other gains an empty one, so it is baked again.
    Its whole-entry fingerprint is cleared either way, since what it was baked from is not known. Returns (entries
    kept, entries to bake again)."""
    by_id = {s["id"]: s for s in slides}
    kept = rebaked = 0
    for slide_id, entry in list(index.items()):
        if (isinstance(entry, dict) and "pixels" in entry) or slide_id not in by_id:
            continue
        current = by_id[slide_id]
        short_id = _short_id(entry)
        same = baked.get(short_id) == lock_files(current, acquired)
        index[slide_id] = {"short_id": short_id, "digest": "", "pixels": pixels_digest(current) if same else ""}
        kept += same
        rebaked += not same
    return kept, rebaked


def _stale(index: dict, slides: list[dict], refresh: set[str]) -> tuple[list[str], list[str]]:
    """Of the baked slides among ``slides``, those to bake again (named in ``refresh``; whose pixels changed; or whose
    entry has no pixels fingerprint, since what changed cannot be told: ``upgrade_entries`` runs first) and those whose
    record alone changed."""
    by_id = {s["id"]: s for s in slides}
    rebake, records = [], []
    for slide_id, entry in index.items():
        if slide_id not in by_id:
            continue  # not among the slides this bake stores: left as it is
        current = by_id[slide_id]
        if slide_id in refresh or not isinstance(entry, dict) or not entry.get("pixels"):
            rebake.append(slide_id)
        elif entry.get("digest") == digest(current):
            continue
        elif entry["pixels"] == pixels_digest(current):
            records.append(slide_id)
        else:
            rebake.append(slide_id)
    return rebake, records


async def _refresh_records(out: Path, index: dict, slide_ids: list[str], slides: list[dict], acquired: dict,
                           vault: Path) -> None:
    """Rewrite the rows of slides whose record changed and whose images did not: every slide column the submission
    sets (country, locality, determination, placement, search text) and the credits of every stored image (licence,
    rights holder, creator, caption, record id), matched to its lock asset by source address and plane. A fused image
    takes the credits of its stack's first plane, as the fusion gave them."""
    by_id = {s["id"]: s for s in slides}
    keep = {"id", "short_id", "status", "published_at", "created_at", "contributor_id"}
    engine = make_async_engine(out / "laminario.sqlite3")
    try:
        async with async_sessions(engine)() as db:
            for slide_id in slide_ids:
                slide = by_id[slide_id]
                short_id = index[slide_id]["short_id"]
                report = validate_submission(submission(slide, acquired, vault))
                if not report.valid:
                    raise ValueError(f"{slide_id} does not validate: {report.errors[:2]}")
                fresh = slide_service.slide_from_submission(report.submission, new_id=short_id,
                                                            resolved=_resolved(slide))
                row = (await db.execute(select(Slide).where(Slide.short_id == short_id))).scalar_one()
                for column in Slide.__table__.columns:
                    if column.name not in keep:
                        setattr(row, column.name, getattr(fresh, column.name))
                row.updated_at = utcnow()
                wanted = {(a.source_url, a.plane_index): a for a in fresh.assets}
                by_url = {a.source_url: a for a in fresh.assets}
                stored = (await db.execute(select(Asset).where(Asset.slide_id == row.id))).scalars().all()
                first_plane: dict[str, Asset] = {}
                for asset in stored:
                    if asset.role in DERIVED_ROLES:
                        continue
                    new = wanted.get((asset.source_url, asset.plane_index))
                    if new is None and asset.role == "slide_overview" and asset.source_url in by_url:
                        # A scanner's photograph kept from the scan's file (U17): credited as the scan, its own
                        # caption kept.
                        scan = by_url[asset.source_url]
                        asset.licence_uri, asset.rights_holder, asset.creator, asset.source_record_id = (
                            scan.licence_uri, scan.rights_holder, scan.creator, scan.source_record_id)
                        continue
                    if new is None:
                        raise ValueError(f"{slide_id}: its stored image from {asset.source_url} (plane "
                                         f"{asset.plane_index}) is not in its lock entry; bake it again")
                    for column in ASSET_CREDIT_COLUMNS:
                        setattr(asset, column, getattr(new, column))
                    if asset.stack and (asset.stack not in first_plane
                                        or asset.plane_index < first_plane[asset.stack].plane_index):
                        first_plane[asset.stack] = asset
                for asset in stored:
                    if asset.role in DERIVED_ROLES and asset.stack in first_plane:
                        plane = first_plane[asset.stack]
                        asset.licence_uri, asset.rights_holder, asset.creator = \
                            plane.licence_uri, plane.rights_holder, plane.creator
                index[slide_id] = {**index[slide_id], "digest": digest(slide), "pixels": pixels_digest(slide)}
            await db.commit()
    finally:
        await engine.dispose()


def _remove(out: Path, index: dict, slide_ids: list[str]) -> None:
    """Take slides out of the bake root: their rows, jobs, journal and stored files."""
    settings = bake_settings(out)
    engine = make_sync_engine(out / "laminario.sqlite3")
    try:
        with engine.begin() as conn:
            for slide_id in slide_ids:
                short_id = _short_id(index.pop(slide_id))
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


def _queue_overviews(out: Path) -> int:
    """Queue the extraction of the scanner's photograph for every baked scan that has none yet (U17): the slide's
    overview is added beside the scan, which is not processed again."""
    from app.jobs.kinds import queue_overview

    engine = make_sync_engine(out / "laminario.sqlite3")
    queued = 0
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT slide_id, MIN(id) FROM asset WHERE family = 'micro' AND media_kind = 'pyramid' "
                "AND role IN ('pyramid', 'z_plane') AND status = 'ready' GROUP BY slide_id")).all()
        for slide_id, asset_id in rows:
            queued += bool(queue_overview(engine, slide_id, asset_id))
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
    acquired = load_acquired()
    if any(not isinstance(entry, dict) or "pixels" not in entry for entry in index.values()):
        kept, rebaked = upgrade_entries(index, lock["slides"], baked_files(out), acquired)
        index_path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
        print(f"{kept + rebaked} index entries made before the pixels fingerprint: {kept} have their images from the "
              f"files the lock names, {rebaked} do not", flush=True)
    stale, records = _stale(index, chosen, refresh or set())
    if stale:
        _remove(out, index, stale)
        index_path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
        print(f"{len(stale)} slides changed since they were baked and are baked again: {', '.join(stale)}", flush=True)
    if records:
        asyncio.run(_refresh_records(out, index, records, lock["slides"], acquired, vault))
        print(f"{len(records)} slides had their record rewritten, their images kept", flush=True)
    created = asyncio.run(_store(out, chosen, acquired, vault, index))
    index_path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    _queue_processing(out, created)
    _run_worker(out)
    if _queue_overviews(out):
        _run_worker(out)
    return write_manifest(out)
