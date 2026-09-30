"""The bake index: which baked slides are baked again, which have their record rewritten, and how an entry made before
the pixels fingerprint is judged by the bake's own rows. Record-only changes end to end: tests/base/test_countries.py.
"""

from __future__ import annotations

from app.base.bake import _stale, digest, lock_files, pixels_digest, upgrade_entries


def _slide(slide_id: str, ref: str, url: str) -> dict:
    return {"id": slide_id, "specimen": {"anchor": {"ref": ref}},
            "assets": [{"url": url, "role": "single", "licence": "CC-BY-4.0", "rights_holder": "A museum"}]}


def test_pixels_and_record_changes_are_told_apart():
    a, b, c = _slide("a", "1", "https://a"), _slide("b", "2", "https://b"), _slide("c", "3", "https://c")
    index = {s["id"]: {"short_id": f"{s['id'].upper() * 4}0001", "digest": digest(s), "pixels": pixels_digest(s)}
             for s in (a, b, c)}
    credited = {**b, "assets": [{**b["assets"][0], "rights_holder": "The same museum, renamed"}]}
    moved = {**c, "assets": [{**c["assets"][0], "url": "https://c2"}]}
    assert _stale(index, [a, credited, moved], set()) == (["c"], ["b"])  # a credit is record; a new file is pixels
    assert _stale(index, [a, credited, moved], {"a"}) == (["a", "c"], ["b"])  # named: baked again
    assert _stale(index, [a], set()) == ([], [])  # slides this bake does not store are left alone
    assert digest(a) == digest({"specimen": {"anchor": {"ref": "1"}}, "assets": a["assets"], "id": "a"})


def test_an_entry_without_a_pixels_fingerprint_is_judged_by_the_stored_images():
    kept, moved, plain = _slide("kept", "1", "https://k"), _slide("moved", "2", "https://m2"), _slide("p", "3", "u")
    acquired = {"https://k": {"sha256": "k" * 64}, "https://m2": {"sha256": "m" * 64}, "u": {"sha256": "u" * 64}}
    index = {"kept": "KEPT0001", "moved": {"short_id": "MOVE0002", "digest": "old", "images": "old"}, "p": "PLAIN003"}
    baked = {"KEPT0001": lock_files(kept, acquired), "MOVE0002": {("https://m1", "m" * 64)},
             "PLAIN003": {("u", "an older download")}}
    assert upgrade_entries(index, [kept, moved, plain], baked, acquired) == (1, 2)
    assert index["kept"] == {"short_id": "KEPT0001", "digest": "", "pixels": pixels_digest(kept)}
    assert index["moved"]["short_id"] == "MOVE0002" and index["moved"]["pixels"] == ""
    # The kept entry's record is rewritten (what it was baked from is not known); the others are baked again.
    assert _stale(index, [kept, moved, plain], set()) == (["moved", "p"], ["kept"])
    assert upgrade_entries(index, [kept, moved, plain], baked, acquired) == (0, 0)  # upgraded once
    assert _stale({"x": "XXXX0001"}, [_slide("x", "9", "v")], set()) == (["x"], [])  # never trusted unjudged
