"""Processing jobs chain the imaging engine and leave the catalog consistent."""

from __future__ import annotations

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text

from app.imaging import edf, reader
from app.jobs import kinds, queue
from app.main import create_app
from app.worker.runner import Worker
from tests.delivery.support import seed_slide
from tests.imaging.synthetic import focal_stack

from .support import job, sandbox

CC_BY = "https://creativecommons.org/licenses/by/4.0/"


@pytest.fixture(scope="module")
def vips():
    try:
        from app.imaging.library import vips as load

        module = load()
        module.version(0)
    except Exception as exc:
        pytest.skip(f"libvips is not available: {exc}")
    return module


def textured(vips, width, height, seed):
    noise = vips.Image.gaussnoise(width, height, sigma=20, mean=120 + seed)
    xy = vips.Image.xyz(width, height)
    stripes = ((xy[0] // (31 + seed) + xy[1] // 47) % 2) * 110 + 70
    return noise.bandjoin([stripes, (noise + stripes) / 2]).cast("uchar")


def asset_row(engine, asset_id):
    with engine.connect() as conn:
        return conn.execute(text("SELECT * FROM asset WHERE id = :id"), {"id": asset_id}).one()


def asset_ids(engine, short_id):
    with engine.connect() as conn:
        return [r.id for r in conn.execute(text(
            "SELECT a.id FROM asset a JOIN slide s ON s.id = a.slide_id WHERE s.short_id = :s ORDER BY a.sort_order"),
            {"s": short_id})]


def run(engine, kind, payload):
    job_id, public_id = queue.enqueue(engine, kind, payload)
    return kinds.execute(job_id, public_id, kind, payload)


# R-401
def test_process_asset_is_idempotent(tmp_path, monkeypatch, vips):
    settings, engine = sandbox(tmp_path, monkeypatch)
    source = tmp_path / "scan.tif"
    textured(vips, 2500, 1800, 0).tiffsave(str(source))
    short = seed_slide(settings, [{"family": "micro", "media_kind": "pyramid", "status": "pending",
                                   "licence_uri": CC_BY, "source_path": str(source), "pixel_size_um": 0.46}])
    asset_id = asset_ids(engine, short)[0]
    first = run(engine, "process_asset", {"asset_id": asset_id})
    again = run(engine, "process_asset", {"asset_id": asset_id})
    assert (again["storage_key"], again["sha256"]) == (first["storage_key"], first["sha256"])
    stored = settings.store_root / first["storage_key"]
    assert stored.is_file() and first["storage_key"].startswith(f"{short}/{asset_id}-")
    row = asset_row(engine, asset_id)
    assert (row.status, row.width_px, row.height_px) == ("ready", 2500, 1800)
    assert row.psnr_db >= 38.0 and row.codec.startswith("jpeg-q") and row.sha256 == first["sha256"]
    assert row.bytes == stored.stat().st_size

    textured(vips, 2500, 1800, 5).tiffsave(str(source))  # the contributor replaces the file
    third = run(engine, "process_asset", {"asset_id": asset_id})
    assert third["storage_key"] != first["storage_key"], "new content, new key: a cached tile never goes stale"
    assert not stored.exists(), "the file of the replaced source is removed"
    assert (settings.store_root / third["storage_key"]).is_file()


# R-402
def test_worker_processes_a_case_end_to_end(tmp_path, monkeypatch, vips):
    settings, engine = sandbox(tmp_path, monkeypatch)
    micro_source = tmp_path / "micro.tif"
    textured(vips, 3000, 2000, 1).tiffsave(str(micro_source))
    photo = tmp_path / "slide.jpg"
    picture = Image.fromarray(np.random.default_rng(2).integers(0, 256, (900, 2600, 3), dtype=np.uint8))
    exif = Image.Exif()
    exif.get_ifd(0x8825)[2] = (33.0, 27.0, 0.0)
    picture.save(photo, exif=exif)
    short = seed_slide(settings, [
        {"family": "micro", "media_kind": "pyramid", "status": "pending", "licence_uri": CC_BY,
         "source_path": str(micro_source)},
        {"family": "macro", "role": "slide_overview", "media_kind": "image", "status": "pending",
         "licence_uri": CC_BY, "source_path": str(photo)},
    ])
    micro_id, macro_id = asset_ids(engine, short)
    jobs = [queue.enqueue(engine, "process_asset", {"asset_id": a})[0] for a in (micro_id, macro_id)]
    assert Worker(settings).run(max_jobs=2) == 2
    assert [job(engine, j).status for j in jobs] == ["succeeded", "succeeded"], [job(engine, j).error for j in jobs]
    macro = asset_row(engine, macro_id)
    assert macro.storage_key.endswith(".jpg") and (macro.width_px, macro.height_px) == (2600, 900)
    assert 0x8825 not in Image.open(settings.store_root / macro.storage_key).getexif(), "no GPS leaves the server"
    with TestClient(create_app(settings)) as client:
        record = client.get(f"/api/slides/{short}").json()
    media = {a["id"]: a["media"] for a in record["assets"]}
    micro = asset_row(engine, micro_id)
    assert media[micro_id]["iiif_info_url"].endswith(micro.storage_key.replace("/", "%2F") + "/info.json")
    assert media[macro_id]["image_url"].endswith("/media/" + macro.storage_key)
    assert record["quality"]["checks"][0]["passed"]


# R-403, R-404
def test_fuse_stack_stores_composites(tmp_path, monkeypatch, vips):
    settings, engine = sandbox(tmp_path, monkeypatch)
    stack, _, truth = focal_stack(300, 420, 10, 3)
    source = tmp_path / "stack.tif"
    tifffile.imwrite(source, stack.astype(np.uint8), imagej=True)
    planes = [{"family": "micro", "role": "z_plane", "media_kind": "pyramid", "status": "pending", "licence_uri": CC_BY,
               "source_path": str(source), "stack": "z1", "plane_index": k, "plane_depth_um": 2.0 * k,
               "pixel_size_um": 0.5} for k in range(10)]
    short = seed_slide(settings, planes)
    for k, asset_id in enumerate(asset_ids(engine, short)):
        run(engine, "process_asset", {"asset_id": asset_id, "plane": k})
    with engine.connect() as conn:
        slide_id = conn.execute(text("SELECT id FROM slide WHERE short_id = :s"), {"s": short}).scalar_one()
        queued = conn.execute(text("SELECT payload_json FROM job "
                                   "WHERE kind = 'fuse_stack' AND status = 'queued'")).all()
    assert len(queued) == 1 and '"stack": "z1"' in queued[0].payload_json, "the last plane queued the fusion, once"
    result = run(engine, "fuse_stack", {"slide_id": slide_id, "stack": "z1"})
    assert set(result["assets"]) == {"edf_wavelet", "edf_variance", "height_map"}
    derived = {role: asset_row(engine, aid) for role, aid in result["assets"].items()}
    assert all(row.status == "ready" and (row.width_px, row.height_px) == (420, 300) for row in derived.values())
    assert derived["edf_wavelet"].psnr_db >= 38 and derived["edf_variance"].psnr_db >= 38

    # the stored height map equals the engine run on the stored planes, and it finds the focus
    stored = [vips.Image.new_from_file(str(settings.store_root / asset_row(engine, a).storage_key))
              for a in asset_ids(engine, short)[:10]]
    reference = edf.fuse(lambda k, x, y, w, h: reader.window(stored[k], x, y, w, h), 10, 420, 300,
                         edf.METHOD_VARIANCE)
    height = np.asarray(Image.open(settings.store_root / derived["height_map"].storage_key)).astype(int)
    assert np.array_equal(height, reference.height_map.astype(int))
    assert np.mean(np.abs(height - truth) <= 1) >= 0.9
    assert "depths [0.0, 2.0" in derived["height_map"].caption

    again = run(engine, "fuse_stack", {"slide_id": slide_id, "stack": "z1"})
    assert again["keys"] == result["keys"] and again["assets"] == result["assets"], "fusion is idempotent"

    with TestClient(create_app(settings)) as client:
        manifest = client.get(f"/api/slides/{short}/manifest").json()
    labels = [canvas["label"]["en"][0] for canvas in manifest["items"]]
    assert len(labels) == 12, "ten planes and two composites; the height map is not painted"
    assert any(label.startswith("extended depth of field, complex wavelets") for label in labels)
