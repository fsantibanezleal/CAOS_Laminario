"""Acquisition names whole-slide files by the extension their source gives them (the reader needs it)."""

from __future__ import annotations

from pathlib import Path

from app.base.acquire import _name_by_extension, _partial, extension_of


def test_extension_comes_from_the_source_file_name():
    zenodo = {"wsi": True, "url": "https://zenodo.org/api/records/18397703/files/a.ndpi/content",
              "record_id": "zenodo:18397703/8_Slide_ostracod_A_specimen_fossil_NMNH.ndpi"}
    assert extension_of(zenodo) == "ndpi"
    assert extension_of({"wsi": True, "record_id": "openslide:DICOM/3DHISTECH-2.zip"}) == "zip"
    assert extension_of({"record_id": "File:Thin section.jpg"}) is None  # images keep the URL's or the type's


def test_files_acquired_under_a_guessed_extension_are_renamed(tmp_path: Path):
    digest = "ab" * 32
    (tmp_path / f"{digest}.bin").write_bytes(b"ndpi bytes")
    asset = {"wsi": True, "url": "https://zenodo.org/x/content", "record_id": "zenodo:1/scan.ndpi"}
    acquired = {asset["url"]: {"sha256": digest, "file": f"{digest}.bin"}}
    assert _name_by_extension({"slides": [{"assets": [asset]}]}, acquired, tmp_path) == 1
    assert acquired[asset["url"]]["file"] == f"{digest}.ndpi"
    assert (tmp_path / f"{digest}.ndpi").read_bytes() == b"ndpi bytes"
    assert _name_by_extension({"slides": [{"assets": [asset]}]}, acquired, tmp_path) == 0


def test_each_url_downloads_into_its_own_partial_file(tmp_path: Path):
    assert _partial(tmp_path, "https://a/1") != _partial(tmp_path, "https://a/2")
    assert _partial(tmp_path, "https://a/1") == _partial(tmp_path, "https://a/1")
