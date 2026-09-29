"""The import refuses a bake whose files do not match its manifest, or whose jobs failed (``app.base.importer``)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.base.importer import MANIFEST, ImportRefused, import_bake, verify
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
