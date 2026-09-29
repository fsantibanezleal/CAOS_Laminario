"""A baked slide whose lock entry changed is baked again; one baked before digests were recorded is trusted."""

from __future__ import annotations

from app.base.bake import _stale, digest


def test_changed_entries_are_stale_and_legacy_entries_are_trusted():
    a = {"id": "a", "specimen": {"anchor": {"ref": "1"}}}
    b = {"id": "b", "specimen": {"anchor": {"ref": "2"}}}
    index = {"a": {"short_id": "AAAA0001", "digest": digest(a)}, "b": {"short_id": "BBBB0002", "digest": digest(b)},
             "c": "CCCC0003"}
    moved = {**b, "specimen": {"anchor": {"ref": "3"}}}
    slides = [a, moved, {"id": "c"}]
    assert _stale(index, slides, set()) == ["b"]
    assert _stale(index, slides, {"c"}) == ["b", "c"]
    assert digest(a) == digest({"specimen": {"anchor": {"ref": "1"}}, "id": "a"})  # key order does not matter


def test_a_slide_the_lock_no_longer_holds_leaves_the_bake(tmp_path, monkeypatch):
    """The bake root mirrors the lock: a dropped slide (the DICOM sample over the size limit, F-043) is removed."""
    import json

    import yaml

    from app.base import bake as bake_module

    out = tmp_path / "bake"
    out.mkdir()
    (out / bake_module.INDEX).write_text(json.dumps({"dropped": {"short_id": "AAAA0001", "digest": "x"}}))
    lock = tmp_path / "lock.yaml"
    lock.write_text(yaml.safe_dump({"slides": []}))
    monkeypatch.setattr(bake_module, "LOCK", lock)
    removed = []

    def remove(out_, index, ids):
        removed.extend(ids)
        for slide_id in ids:
            index.pop(slide_id)

    monkeypatch.setattr(bake_module, "_remove", remove)
    monkeypatch.setattr(bake_module, "_store", lambda *a, **k: _done([]))
    monkeypatch.setattr(bake_module, "load_acquired", lambda: {})
    monkeypatch.setattr(bake_module, "_queue_processing", lambda *a: 0)
    monkeypatch.setattr(bake_module, "_run_worker", lambda *a: 0)
    monkeypatch.setattr(bake_module, "write_manifest", lambda out_: {"slides": []})
    bake_module.bake(out, tmp_path)
    assert removed == ["dropped"]
    assert json.loads((out / bake_module.INDEX).read_text()) == {}


async def _done(value):
    return value
