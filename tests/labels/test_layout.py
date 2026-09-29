"""R-1101 and R-1102: the slide's one layout in millimetres, and what its labels carry."""

from __future__ import annotations

import pytest

from app.labels.layout import ADVANCE_EM, MARGIN, QR_MIN_MM, collections_date, label_width, slide_layout
from tests.labels.support import record

FORMATS = [("iso_76x26", (76, 26)), ("us_75x25", (75, 25)), ("petro_27x46", (46, 27)), ("us_2x3in", (76.2, 50.8))]


def _boxes(lay, role):
    return [b for b in lay.boxes if b.role == role]


@pytest.mark.parametrize("fmt,size", FORMATS)
@pytest.mark.parametrize("cover", ["22x22", "22x40", "24x60", "none"])
def test_every_format_is_drawn_at_its_size(fmt, size, cover):
    lay = slide_layout(record(slide={"format": fmt, "coverslip": cover}))
    glass = _boxes(lay, "glass")[0]
    assert (glass.w, glass.h) == size and (lay.long, lay.short) == size
    labels = _boxes(lay, "label")
    assert labels[0].x == 0 and labels[0].w == label_width(size[0]) and labels[0].h == size[1]
    covers = _boxes(lay, "coverslip")
    if cover == "none":
        assert not covers
        return
    box = covers[0]
    right = labels[1].x if len(labels) > 1 else lay.long
    # Centred between the labels, inside the glass, at its recorded size unless the glass is smaller.
    assert box.x + box.w / 2 == pytest.approx((labels[0].w + right) / 2)
    assert box.y + box.h / 2 == pytest.approx(lay.short / 2)
    assert 0 < box.x and box.x + box.w <= right and 0 < box.y and box.y + box.h < lay.short
    long_mm, short_mm = {"22x22": (22, 22), "22x40": (40, 22), "24x60": (60, 24)}[cover]
    assert box.w == min(long_mm, lay.long - labels[0].w - 2) and box.h == min(short_mm, lay.short - 2)


def test_an_assumed_format_is_said_in_words():
    lay = slide_layout(record(slide={"format_assumed": True}))
    note = [ln for ln in lay.lines if ln.role == "note"]
    assert len(note) == 1 and "assumed" in note[0].text and note[0].width <= lay.long
    assert lay.height > lay.short and note[0].baseline < lay.height
    es = slide_layout(record(slide={"format_assumed": True}), "es")
    assert "supuesto" in next(ln.text for ln in es.lines if ln.role == "note")
    assert not [ln for ln in slide_layout(record()).lines if ln.role == "note"]


def _inside(line, box) -> bool:
    return box.x - 1e-6 <= line.x and line.x + line.width <= box.x + box.w + 1e-6


def test_quiet_zone_and_contents():
    # A 22 x 22 coverslip leaves 17 mm of glass beside it: room for the data label.
    lay = slide_layout(record(slide={"coverslip": "22x22"}, specimen={"type_status": "holotype"}))
    frosted, data = _boxes(lay, "label")
    qx, qy, qw, qh = lay.qr.quiet
    # The quiet zone is paper inside the frosted label, and no text enters it.
    assert frosted.x <= qx and qx + qw <= frosted.x + frosted.w and 0 <= qy and qy + qh <= frosted.h
    for line in lay.lines:
        bottom = line.baseline + 0.25 * line.size
        overlaps = line.x < qx + qw and line.x + line.width > qx and line.top < qy + qh and bottom > qy
        assert not overlaps, line.text
    # Every line stays inside its label's margins.
    for line in lay.lines:
        box = frosted if line.x < frosted.w else data
        assert _inside(line, box) and line.x + line.width <= box.x + box.w - MARGIN + 1e-6, line.text
    left = [ln for ln in lay.lines if ln.x < frosted.w]
    right = [ln for ln in lay.lines if ln.x >= data.x]
    assert left[0].text == "LAM-0001" and left[0].runs[0].style == "bold"
    name = [r for ln in left[1:] for r in ln.runs]
    assert [r.style for r in name if r.text.strip() in ("Polyplax", "borealis")] == ["italic", "italic"]
    assert _boxes(lay, "band")[0].w == frosted.w
    # The data label is 15 mm wide: its entries wrap, so its text is read as a whole.
    written = " ".join(ln.text for ln in right)
    assert right[0].text == "HOLOTYPE" and right[0].tone == "type"
    for entry in ("Whole mount, unstained", "Near a stream, Chile", "20.IV.2019", "leg. A. Collector",
                  "prep. A. Preparator"):
        assert entry in written, entry  # Chile: the country the coordinates lie in


def test_without_room_for_a_data_label_the_data_follows_the_name():
    lay = slide_layout(record(slide={"coverslip": "24x60"}))
    assert len(_boxes(lay, "label")) == 1
    assert lay.qr.side + 8 * lay.qr.module >= QR_MIN_MM - 1e-6
    texts = [ln.text for ln in lay.lines]
    assert texts[0] == "LAM-0001" and "Polyplax" in texts[1]
    assert len(texts) > 2  # data lines follow while they fit


def test_a_long_word_breaks_with_a_hyphen_and_lines_fit():
    lay = slide_layout(record(specimen={"anchor": {"kind": "rock", "ref": "natrocarbonatite",
                                                   "name": "natrocarbonatite"}},
                              drop=("host",)))
    frosted = _boxes(lay, "label")[0]
    width = int((frosted.w - 2 * MARGIN) / (ADVANCE_EM * lay.lines[0].size))
    assert all(len(ln.text) <= width for ln in lay.lines if ln.x < frosted.w)
    assert any(ln.text.endswith("-") for ln in lay.lines)


def test_collection_dates():
    assert collections_date("1962-08-31") == "31.VIII.1962"
    assert collections_date("1934-05") == "V.1934"
    assert collections_date("1966") == "1966"
    assert collections_date(None) is None


def test_a_photograph_lies_the_way_the_window_does():
    standing = slide_layout(record(overview=(1000, 3000)))
    assert standing.mount and standing.mount.turned and standing.mount.href.endswith("/media/9422P6AW/1-photo.jpg")
    lying = slide_layout(record(overview=(3000, 1000)))
    assert lying.mount and not lying.mount.turned
    from app.labels import svg

    drawn = svg.render(standing, standalone=False)
    assert 'transform="rotate(90' in drawn and "<style>" not in drawn
