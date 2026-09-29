"""What each kind of job does. Everything here runs in the worker's child process (``execute``).

A job function receives a ``Context`` (the job, the settings, a database engine opened in the child, and
``progress`` to write events) and its payload, and returns a JSON-able result. Steps are idempotent: a job
interrupted by a restart runs again from the start and produces the same outputs.

- ``probe``: sleeps in steps and writes a small file. The worker's own health check and the gates' job.
- ``process_asset``: reads an asset's source file through the U2 reader, writes its pyramid (measured
  fidelity) or its clean image, and marks the asset ready with its dimensions, bytes, SHA-256 and PSNR.
- ``fuse_stack``: fuses the ready focal planes of one stack (U2's extended depth of field) into two composite
  pyramids (complex wavelets, the default image; variance selection) and the variance height map, the depth
  readout, each stored as an asset of the slide.

**Storage keys are content addresses.** A key is ``{short id}/{asset id}-{digest}.{ext}``, the digest taken
from the source's SHA-256 (or the planes' keys) and ``PIPELINE_VERSION``. Re-running a job writes the same
key and the same bytes, and a new source or a new pipeline always writes a new key, so a tile cached under a
key never goes stale (U3).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import Settings
from app.db.engine import database_path, make_sync_engine
from app.jobs import journal

PIPELINE_VERSION = "u4-1"
HASH_CHUNK = 8 * 1024 * 1024
DERIVED_ROLES = ("edf_wavelet", "edf_variance", "height_map")


@dataclass
class Context:
    job_id: int
    public_id: str
    settings: Settings
    engine: Engine

    def progress(self, event: str = "progress", **data) -> None:
        journal.record(self.engine, self.job_id, event, data)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def content_key(short_id: str, asset_id: int, parts: list[str], extension: str) -> str:
    digest = hashlib.sha256("|".join([PIPELINE_VERSION, *parts]).encode("utf-8")).hexdigest()[:12]
    return f"{short_id}/{asset_id}-{digest}.{extension}"


# --- probe --------------------------------------------------------------------------------------------------


def probe(ctx: Context, payload: dict) -> dict:
    steps = int(payload.get("steps", 3))
    seconds = float(payload.get("seconds", 1.0))
    for step in range(steps):
        time.sleep(seconds / max(steps, 1))
        ctx.progress(step=step + 1, of=steps)
    folder = ctx.settings.data_root / "probes"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{ctx.public_id}.txt"
    content = f"probe {ctx.public_id} steps={steps} seconds={seconds:g}\n"
    target.write_text(content, encoding="utf-8")
    return {"output": f"probes/{target.name}", "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}


# --- processing ---------------------------------------------------------------------------------------------


def _asset(engine: Engine, asset_id: int):
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT a.id, a.family, a.role, a.media_kind, a.source_path, a.pixel_size_um, a.stack, a.plane_index, "
            "a.storage_key, a.licence_uri, a.creator, a.rights_holder, s.id AS slide_id, s.short_id "
            "FROM asset a JOIN slide s ON s.id = a.slide_id WHERE a.id = :id"), {"id": asset_id}).first()
    if row is None:
        raise LookupError(f"no asset {asset_id}")
    return row


def _remove_stale(store: Path, short_id: str, asset_id: int, keep: str) -> None:
    """Files of an asset from earlier pipelines or sources; the kept key stays."""
    folder = store / short_id
    if folder.is_dir():
        for path in folder.glob(f"{asset_id}-*"):
            if f"{short_id}/{path.name}" != keep and ".webp-candidate" not in path.name:
                path.unlink(missing_ok=True)


def process_asset(ctx: Context, payload: dict) -> dict:
    from app.imaging import derivatives, pyramid, reader

    asset = _asset(ctx.engine, int(payload["asset_id"]))
    source = Path(payload.get("source_path") or asset.source_path or "")
    if not source.is_file():
        raise FileNotFoundError(f"the source of asset {asset.id} is not on disk: {source}")
    info = reader.read_info(source)
    plane = int(payload.get("plane", 0))
    ctx.progress(step="read", width=info.width, height=info.height, planes=len(info.planes), loader=info.loader)
    source_sha = payload.get("source_sha256") or file_sha256(source)
    store = ctx.settings.store_root
    image = reader.open_plane(info, plane)
    mpp = asset.pixel_size_um or info.mpp_x
    if asset.media_kind == "image":
        key = content_key(asset.short_id, asset.id, [source_sha, str(plane), "image"], "jpg")
        target = store / key
        derivatives.save_clean(image, target, quality=90)
        codec, quality, psnr = "jpeg", 90, None
    else:
        codec_wanted = payload.get("codec", "jpeg")
        key = content_key(asset.short_id, asset.id, [source_sha, str(plane), codec_wanted], "tif")
        target = store / key
        ctx.progress(step="pyramid", key=key)
        written = pyramid.write_pyramid(image, target, mpp, codec=codec_wanted)
        codec, quality, psnr = written.codec, written.quality, round(written.psnr_db, 2)
    _remove_stale(store, asset.short_id, asset.id, key)
    size = target.stat().st_size
    sha = file_sha256(target)
    with ctx.engine.begin() as conn:
        conn.execute(text("UPDATE asset SET storage_key = :key, width_px = :w, height_px = :h, bytes = :bytes, "
                          "sha256 = :sha, psnr_db = :psnr, codec = :codec, status = 'ready', "
                          "pixel_size_um = COALESCE(pixel_size_um, :mpp) WHERE id = :id"),
                     {"key": key, "w": image.width, "h": image.height, "bytes": size, "sha": sha, "psnr": psnr,
                      "codec": f"{codec}-q{quality}", "mpp": mpp, "id": asset.id})
    ctx.progress(step="stored", key=key, bytes=size, psnr_db=psnr)
    return {"asset_id": asset.id, "storage_key": key, "width": image.width, "height": image.height, "bytes": size,
            "sha256": sha, "psnr_db": psnr, "codec": codec, "quality": quality}


def _derived_asset(conn, slide_id: int, template, role: str, media_kind: str, order: int) -> int:
    existing = conn.execute(text("SELECT id FROM asset WHERE slide_id = :s AND stack = :stack AND role = :role"),
                            {"s": slide_id, "stack": template.stack, "role": role}).scalar()
    if existing:
        return existing
    return conn.execute(text(
        "INSERT INTO asset (slide_id, family, role, sort_order, media_kind, status, stack, licence_uri, creator, "
        "rights_holder, modality, created_at) VALUES (:s, 'micro', :role, :order, :kind, 'pending', :stack, "
        ":licence, :creator, :holder, 'brightfield', CURRENT_TIMESTAMP) RETURNING id"),
        {"s": slide_id, "role": role, "order": order, "kind": media_kind, "stack": template.stack,
         "licence": template.licence_uri, "creator": template.creator, "holder": template.rights_holder},
    ).scalar_one()


def fuse_stack(ctx: Context, payload: dict) -> dict:
    import numpy as np

    from app.imaging import edf, pyramid, reader
    from app.imaging.library import vips

    slide_id, stack = int(payload["slide_id"]), str(payload["stack"])
    with ctx.engine.connect() as conn:
        planes = conn.execute(text(
            "SELECT a.id, a.storage_key, a.plane_index, a.plane_depth_um, a.pixel_size_um, a.stack, a.licence_uri, "
            "a.creator, a.rights_holder, s.short_id FROM asset a JOIN slide s ON s.id = a.slide_id "
            "WHERE a.slide_id = :s AND a.stack = :stack AND a.role = 'z_plane' AND a.status = 'ready' "
            "ORDER BY a.plane_index"), {"s": slide_id, "stack": stack}).all()
    if len(planes) < 2:
        raise ValueError(f"stack {stack} of slide {slide_id} has {len(planes)} ready plane(s); fusion needs two")
    store = ctx.settings.store_root
    images = [vips().Image.new_from_file(str(store / p.storage_key)) for p in planes]
    width, height = images[0].width, images[0].height
    if any((im.width, im.height) != (width, height) for im in images):
        raise ValueError("the planes of a stack must share their dimensions")

    def read(k: int, x: int, y: int, w: int, h: int):
        return reader.window(images[k], x, y, w, h)

    ctx.progress(step="fuse", planes=len(planes), width=width, height=height)
    results = {}
    for method, role in ((edf.METHOD_WAVELET, "edf_wavelet"), (edf.METHOD_VARIANCE, "edf_variance")):
        fused = edf.fuse(read, len(planes), width, height, method,
                         progress=lambda done, total, m=method: ctx.progress(step=m, tile=done, of=total))
        results[role] = fused
    template = planes[0]
    parts = [stack] + [p.storage_key for p in planes]
    written = {}
    module = vips()
    with ctx.engine.begin() as conn:
        ids = {role: _derived_asset(conn, slide_id, template, role, kind, order)
               for order, (role, kind) in enumerate((("edf_wavelet", "pyramid"), ("edf_variance", "pyramid"),
                                                     ("height_map", "image")), start=1000)}
    for role in ("edf_wavelet", "edf_variance"):
        composite = results[role].composite
        image = module.Image.new_from_array(composite) if composite.ndim == 2 else \
            module.Image.new_from_memory(np.ascontiguousarray(composite).tobytes(), width, height, 3, "uchar")
        key = content_key(template.short_id, ids[role], [*parts, role], "tif")
        out = pyramid.write_pyramid(image, store / key, template.pixel_size_um)
        written[role] = (key, out)
        _remove_stale(store, template.short_id, ids[role], key)
    height_map = results["edf_variance"].height_map.astype(np.uint16)
    hm_key = content_key(template.short_id, ids["height_map"], [*parts, "height_map"], "png")
    hm_path = store / hm_key
    hm_path.parent.mkdir(parents=True, exist_ok=True)
    module.Image.new_from_memory(np.ascontiguousarray(height_map).tobytes(), width, height, 1, "ushort") \
        .pngsave(str(hm_path), keep="none")
    _remove_stale(store, template.short_id, ids["height_map"], hm_key)
    depths = [p.plane_depth_um for p in planes]
    with ctx.engine.begin() as conn:
        for role, (key, out) in written.items():
            path = store / key
            conn.execute(text("UPDATE asset SET storage_key = :key, width_px = :w, height_px = :h, bytes = :b, "
                              "sha256 = :sha, psnr_db = :psnr, codec = :codec, pixel_size_um = :mpp, "
                              "caption = :caption, status = 'ready' WHERE id = :id"),
                         {"key": key, "w": width, "h": height, "b": path.stat().st_size, "sha": file_sha256(path),
                          "psnr": round(out.psnr_db, 2), "codec": f"{out.codec}-q{out.quality}",
                          "mpp": template.pixel_size_um, "id": ids[role],
                          "caption": ("extended depth of field, complex wavelets" if role == "edf_wavelet"
                                      else "extended depth of field, variance selection")})
        conn.execute(text("UPDATE asset SET storage_key = :key, width_px = :w, height_px = :h, bytes = :b, "
                          "sha256 = :sha, caption = :caption, status = 'ready' WHERE id = :id"),
                     {"key": hm_key, "w": width, "h": height, "b": hm_path.stat().st_size,
                      "sha": file_sha256(hm_path), "id": ids["height_map"],
                      "caption": "height map: 1-based index of the in-focus plane; depths " + json.dumps(depths)})
    ctx.progress(step="stored", assets=ids)
    return {"stack": stack, "planes": len(planes), "assets": ids,
            "keys": {role: key for role, (key, _) in written.items()} | {"height_map": hm_key}}


# --- dispatch -----------------------------------------------------------------------------------------------

KINDS: dict[str, Callable[[Context, dict], dict]] = {
    "probe": probe,
    "process_asset": process_asset,
    "fuse_stack": fuse_stack,
}


def execute(job_id: int, public_id: str, kind: str, payload: dict) -> dict:
    """Entry point in the child process: open the database, run the job, return its result."""
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    settings = Settings()
    engine = make_sync_engine(database_path(settings))
    try:
        ctx = Context(job_id=job_id, public_id=public_id, settings=settings, engine=engine)
        ctx.progress("log", pid=os.getpid(), kind=kind)
        return KINDS[kind](ctx, payload)
    finally:
        engine.dispose()
