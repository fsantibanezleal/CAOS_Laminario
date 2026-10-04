"""R-1203: a photograph of a private case that still carries its GPS position is refused at verification, with the
reason; the same photograph with its GPS directory emptied (what the contribute page leaves) is accepted, and an open
case keeps the position in its original (only the published cell and the derivatives, without EXIF, are public)."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from app.jobs.kinds import has_gps
from tests.uploads.test_tus import rows, run_worker

from .support import contributor, create, patch, settings_for, upload_stack, wait_for_upload

GPS_IFD = 0x8825


def photo(gps: dict | None, seed: int = 3) -> bytes:
    """A JPEG with a date in its EXIF and, when given, a GPS directory (an empty one when ``gps`` is {})."""
    pixels = np.random.default_rng(seed).integers(0, 256, (600, 900, 3), dtype=np.uint8)
    exif = Image.Exif()
    exif[0x0132] = "2019:04:20 10:00:00"
    if gps is not None:
        exif[GPS_IFD] = gps
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="JPEG", quality=90, exif=exif.tobytes())
    return buffer.getvalue()


SANTIAGO = {1: "S", 2: (33.0, 26.0, 56.0), 3: "W", 4: (70.0, 39.0, 0.0)}


def test_the_check_reads_the_position(tmp_path):
    # has_gps reads a JPEG through libvips. Its neighbours skip without the library (through tusd's stack or the
    # imaging fixture); this one failed instead wherever libvips is absent.
    try:
        from app.imaging.library import vips

        vips().version(0)
    except Exception as exc:  # the library is absent or cannot be loaded on this machine
        pytest.skip(f"libvips is not available: {exc}")
    with_position, emptied, without = tmp_path / "a.jpg", tmp_path / "b.jpg", tmp_path / "c.jpg"
    with_position.write_bytes(photo(SANTIAGO))
    emptied.write_bytes(photo({}))
    without.write_bytes(photo(None))
    assert has_gps(with_position, "jpeg")
    assert not has_gps(emptied, "jpeg") and not has_gps(without, "jpeg")


def send(stack: dict, cookie: dict, slide: str, asset: int, data: bytes) -> None:
    created = create(stack, len(data), cookie, slide=slide, asset=str(asset), filename="place.jpg",
                     filetype="image/jpeg")
    assert created.status_code == 201, created.text
    assert patch(created.headers["Location"], 0, data, cookie).status_code == 204


def test_a_private_case_refuses_a_photograph_with_its_position(tmp_path, monkeypatch):
    with upload_stack(settings_for(tmp_path)) as stack:
        cookie, slide, assets = contributor(stack)
        settings = stack["settings"]
        from sqlalchemy import create_engine, text

        engine = create_engine(f"sqlite:///{(settings.data_root / 'laminario.sqlite3').as_posix()}")
        with engine.begin() as conn:
            conn.execute(text("UPDATE slide SET geoprivacy = 'private' WHERE short_id = :s"), {"s": slide})
        engine.dispose()

        send(stack, cookie, slide, assets[0], photo(SANTIAGO))
        wait_for_upload(settings, "received")
        run_worker(settings, monkeypatch, 1)
        refused = rows(settings, "SELECT status, reason FROM upload ORDER BY id")[-1]
        assert refused.status == "rejected" and "GPS position" in refused.reason
        folder = settings.sources_root / slide
        assert not folder.exists() or not any(folder.iterdir()), "a refused file is not kept"

        send(stack, cookie, slide, assets[0], photo({}))
        wait_for_upload(settings, "received")
        run_worker(settings, monkeypatch, 2)
        accepted = rows(settings, "SELECT status, reason FROM upload ORDER BY id")[-1]
        assert accepted.status == "accepted", accepted.reason


def test_an_open_case_keeps_the_position(tmp_path, monkeypatch):
    with upload_stack(settings_for(tmp_path)) as stack:
        cookie, slide, assets = contributor(stack)
        settings = stack["settings"]
        send(stack, cookie, slide, assets[0], photo(SANTIAGO))
        wait_for_upload(settings, "received")
        run_worker(settings, monkeypatch, 2)
        upload = rows(settings, "SELECT status, reason FROM upload ORDER BY id")[-1]
        assert upload.status == "accepted", upload.reason
