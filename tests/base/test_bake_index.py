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
