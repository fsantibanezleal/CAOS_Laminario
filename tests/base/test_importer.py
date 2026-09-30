"""The import refuses a bake whose files do not match its manifest, or whose jobs failed (``app.base.importer``)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.base.importer import MANIFEST, ImportRefused, import_bake, manifest_files, place, verify
from app.config import Settings


def _bake(root: Path, content: bytes = b"pyramid bytes", failed_jobs: int = 0) -> dict:
    key = "ab/abcdef/pyramid.tif"
    (root / "store" / key).parent.mkdir(parents=True)
    (root / "store" / key).write_bytes(content)
    manifest = {"failed_jobs": failed_jobs, "taxa": [], "slides": [{"slide": {"short_id": "base0001"}, "assets": [
        {"file": {"key": key, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}}]}]}
    (root / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def test_verify_finds_a_changed_and_a_missing_file(tmp_path: Path):
    manifest = _bake(tmp_path)
    assert verify(tmp_path, manifest) == []
    key = manifest["slides"][0]["assets"][0]["file"]["key"]
    (tmp_path / "store" / key).write_bytes(b"pyramid bytez")
    assert verify(tmp_path, manifest) == [f"{key}: differs from the manifest"]
    (tmp_path / "store" / key).unlink()
    assert verify(tmp_path, manifest) == [f"{key}: missing"]


def test_import_refuses_a_tampered_or_failed_bake(tmp_path: Path):
    bake = tmp_path / "bake"
    manifest = _bake(bake)
    key = manifest["slides"][0]["assets"][0]["file"]["key"]
    (bake / "store" / key).write_bytes(b"other bytes")
    target = Settings(data_root=tmp_path / "server")
    with pytest.raises(ImportRefused, match="differs from the manifest"):
        import_bake(bake, target)
    assert not (tmp_path / "server" / "laminario.sqlite3").exists()

    failed = tmp_path / "failed"
    _bake(failed, failed_jobs=2)
    with pytest.raises(ImportRefused, match="2 failed jobs"):
        import_bake(failed, target)


def test_the_served_store_is_checked_against_the_manifest_after_an_import(tmp_path: Path):
    """R-1603: after an import, every file the manifest lists is in the served store with its SHA-256 and size."""
    import shutil

    bake = tmp_path / "bake"
    manifest = _bake(bake)
    target = Settings(data_root=tmp_path / "server")
    shutil.copytree(bake / "store", target.store_root)  # what the import's copy leaves in the served store
    assert manifest_files(manifest) == 1 and verify(bake, manifest, target.store_root) == []
    key = manifest["slides"][0]["assets"][0]["file"]["key"]
    (target.store_root / key).write_bytes(b"a served file changed")
    assert verify(bake, manifest, target.store_root) == [f"{key}: differs from the manifest"]
    assert verify(bake, manifest) == []  # the bake's own store is untouched


def test_a_file_is_linked_on_one_volume_and_copied_across(tmp_path: Path, monkeypatch):
    """On the host the bake and the store share the data volume: a hard link places a file with no second copy (an
    import of 44 GB would otherwise need 44 GB more). Across volumes the file is copied. Either way the target is the
    source's bytes, and a different file already at the target is replaced."""
    import os

    source = tmp_path / "bake" / "a.tif"
    source.parent.mkdir()
    source.write_bytes(b"pyramid bytes")
    target = tmp_path / "store" / "ab" / "a.tif"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"a stale file")
    assert place(source, target) == "linked"
    assert target.read_bytes() == b"pyramid bytes" and os.stat(target).st_nlink == 2
    source.unlink()  # the staged bake is removed after the import: the stored file stays
    assert target.read_bytes() == b"pyramid bytes"

    source.write_bytes(b"other bytes")

    def no_links(*_):
        raise OSError(18, "Invalid cross-device link")

    monkeypatch.setattr(os, "link", no_links)
    assert place(source, target) == "copied"
    assert target.read_bytes() == b"other bytes" and os.stat(target).st_nlink == 1
