"""Resumable uploads through tusd and the API's hooks, verified and handed to the worker."""

from __future__ import annotations

import hashlib
import io
import time

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import create_engine, text

from app.worker.runner import Worker

from .support import (
    contributor, create, interrupted_patch, offset, patch, settings_for, upload_stack, wait_for_upload,
)


def photo_bytes(width: int = 1600, height: int = 1100, seed: int = 0) -> bytes:
    pixels = np.random.default_rng(seed).integers(0, 256, (height, width, 3), dtype=np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="TIFF")
    return buffer.getvalue()


def rows(settings, sql: str, **params):
    engine = create_engine(f"sqlite:///{(settings.data_root / 'laminario.sqlite3').as_posix()}")
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql), params).all()
    finally:
        engine.dispose()


def run_worker(settings, monkeypatch, jobs: int) -> int:
    monkeypatch.setenv("LAMINARIO_DATA_ROOT", str(settings.data_root))
    return Worker(settings).run(max_jobs=jobs, deadline=time.monotonic() + 300)


# R-040
def test_resume_after_interruption(tmp_path, monkeypatch):
    data = photo_bytes()
    original = hashlib.sha256(data).hexdigest()
    with upload_stack(settings_for(tmp_path)) as stack:
        cookie, slide, assets = contributor(stack)
        created = create(stack, len(data), cookie, slide=slide, asset=str(assets[1]), filename="scan.tif",
                         filetype="image/tiff")
        assert created.status_code == 201, created.text
        location = created.headers["Location"]
        interrupted_patch(location, 0, data, cookie, send=len(data) // 2)
        reached = offset(location, cookie)
        assert 0 < reached < len(data), f"an interrupted upload keeps what arrived ({reached} of {len(data)})"
        finished = patch(location, reached, data[reached:], cookie)
        assert finished.status_code == 204 and int(finished.headers["Upload-Offset"]) == len(data)
        settings = stack["settings"]
        wait_for_upload(settings, "received")
    assert run_worker(settings, monkeypatch, 2) == 2  # verification, then processing
    upload = rows(settings, "SELECT status, sha256, sniffed, source_path, reason FROM upload")[0]
    assert upload.status == "accepted", upload.reason
    assert upload.sha256 == original, "the resumed upload has the original's SHA-256"
    assert upload.sniffed == "tiff"
    with open(upload.source_path, "rb") as source:
        assert hashlib.sha256(source.read()).hexdigest() == original
    asset = rows(settings, "SELECT status, width_px, height_px, source_sha256 FROM asset WHERE id = :id",
                 id=assets[1])[0]
    assert (asset.status, asset.width_px, asset.height_px) == ("ready", 1600, 1100)
    assert asset.source_sha256 == original, "the image keeps the SHA-256 of the file it was made from (R-1208)"
    assert not list(settings.quarantine_root.iterdir()), "the quarantine is empty once the file is accepted"


# R-041
def test_disallowed_type_rejected(tmp_path, monkeypatch):
    program = b"MZ\x90\x00" + bytes(range(256)) * 40
    with upload_stack(settings_for(tmp_path)) as stack:
        cookie, slide, assets = contributor(stack)
        location = create(stack, len(program), cookie, slide=slide, asset=str(assets[1]),
                          filename="innocent.jpg").headers["Location"]
        assert patch(location, 0, program, cookie).status_code == 204
        settings = stack["settings"]
        wait_for_upload(settings, "received")
    assert run_worker(settings, monkeypatch, 1) == 1
    upload = rows(settings, "SELECT status, sniffed, reason FROM upload")[0]
    assert upload.status == "rejected" and upload.sniffed == "refused"
    assert "a Windows executable" in upload.reason and "accepted are JPEG" in upload.reason
    assert not list(settings.quarantine_root.iterdir()), "the refused file is deleted from quarantine"
    assert rows(settings, "SELECT status FROM asset WHERE id = :id", id=assets[1])[0].status == "pending"
    assert rows(settings, "SELECT COUNT(*) AS n FROM job WHERE kind = 'process_asset'")[0].n == 0


# R-042
def test_quota_refused(tmp_path):
    with upload_stack(settings_for(tmp_path, quota_bytes=50_000, quota_wsi=0)) as stack:
        cookie, slide, assets = contributor(stack)
        too_big = create(stack, 60_000, cookie, slide=slide, asset=str(assets[1]), filename="photo.jpg")
        assert too_big.status_code == 413 and "left of its" in too_big.json()["detail"]
        scanner = create(stack, 10_000, cookie, slide=slide, asset=str(assets[1]), filename="slide.ndpi")
        assert scanner.status_code == 413 and "whole-slide images" in scanner.json()["detail"]
        fits = create(stack, 10_000, cookie, slide=slide, asset=str(assets[1]), filename="photo.jpg")
        assert fits.status_code == 201
        settings = stack["settings"]
    assert len(rows(settings, "SELECT id FROM upload")) == 1, "refused uploads never start"


# R-043
def test_tier_a_budget_blocks_wsi(tmp_path):
    with upload_stack(settings_for(tmp_path, wsi_block_fraction=0.0)) as stack:  # any use counts as over the line
        cookie, slide, assets = contributor(stack)
        scanner = create(stack, 10_000, cookie, slide=slide, asset=str(assets[1]), filename="specimen.svs")
        assert scanner.status_code == 507
        assert "percent full; whole-slide uploads resume" in scanner.json()["detail"]
        photo = create(stack, 10_000, cookie, slide=slide, asset=str(assets[0]), filename="slide.jpg")
        assert photo.status_code == 201, "photographs still go"


def test_uploads_are_authorised(tmp_path):
    with upload_stack(settings_for(tmp_path)) as stack:
        cookie, slide, assets = contributor(stack)
        anonymous = create(stack, 1000, {}, slide=slide, asset=str(assets[1]), filename="a.jpg")
        assert anonymous.status_code == 401
        other_cookie, other_slide, _ = contributor(stack, "other@example.org")
        foreign = create(stack, 1000, other_cookie, slide=slide, asset=str(assets[1]), filename="a.jpg")
        assert foreign.status_code == 403, "a contributor uploads only to its own cases"
        missing = create(stack, 1000, cookie, slide=slide, asset="999999", filename="a.jpg")
        assert missing.status_code == 404
        first = create(stack, 1000, cookie, slide=slide, asset=str(assets[1]), filename="a.jpg")
        second = create(stack, 1000, cookie, slide=slide, asset=str(assets[1]), filename="a.jpg")
        assert (first.status_code, second.status_code) == (201, 409), "one upload at a time per image"


@pytest.mark.parametrize("kind", ["zip-mrxs", "zip-other"])
def test_archives_are_recognised(tmp_path, kind):
    import zipfile

    from app.uploads.sniff import sniff

    archive = tmp_path / "slide.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("slide/slide.mrxs" if kind == "zip-mrxs" else "notes.txt", b"x")
    found = sniff(archive)
    assert found.kind == kind and found.accepted == (kind == "zip-mrxs")


# R-501
def test_tusd_compose_file_on_loopback(tmp_path):
    """The production compose file: pinned image, host network on loopback, read-only, hooks reaching the API."""
    import os
    import subprocess
    import sys

    from tests.delivery.support import docker, free_port, wait_for_http

    from .support import TUS_IMAGE, compose_tusd

    exe = docker()
    if sys.platform != "linux":
        pytest.skip("the tusd compose file uses host networking, which needs a Linux container engine")
    settings = settings_for(tmp_path)
    os.chmod(settings.quarantine_root, 0o777)  # the container's user writes here
    with upload_stack(settings) as stack:
        cookie, slide, assets = contributor(stack)
        api_port = stack["api"].rsplit(":", 1)[1]
        port = free_port()
        with compose_tusd(settings.quarantine_root, port, int(api_port), f"laminario-test-{os.getpid()}") as name:
            wait_for_http(f"http://127.0.0.1:{port}/files/")
            probe = {"tus": f"http://127.0.0.1:{port}/files/"}
            created = create(probe, 1000, cookie, slide=slide, asset=str(assets[1]), filename="a.jpg")
            assert created.status_code == 201, created.text
            refused = create(probe, 1000, {}, slide=slide, asset=str(assets[0]), filename="b.jpg")
            assert refused.status_code == 401, "the hook ran and saw no session"
            fmt = "{{.Config.Image}}|{{.HostConfig.ReadonlyRootfs}}|{{.HostConfig.NetworkMode}}|{{json .Args}}"
            image, readonly, network, args = subprocess.run(
                [exe, "inspect", name, "--format", fmt], capture_output=True, text=True, check=True,
                timeout=60).stdout.strip().split("|")
            assert image == TUS_IMAGE and readonly == "true" and network == "host"
            assert "-host=127.0.0.1" in args and "-hooks-http-forward-headers=Cookie" in args
