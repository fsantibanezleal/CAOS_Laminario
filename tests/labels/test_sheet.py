"""R-1404 to R-1406: label stocks as data, labels fitted to their cells, and the test page measured at 1:1."""

from __future__ import annotations

import io
import re

import pytest
from pypdf import PdfReader

from app.labels import sheet
from app.labels.cell import INSET, fit
from app.labels.pdf import MM
from app.labels.stocks import positions, stocks
from tests.labels.support import record

NUMBER = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
#: The layout rounds positions to 0.1 um; a micrometre is the precision the checks ask for.
EPS = 1e-3


@pytest.mark.parametrize("stock_id", sorted(stocks()))
def test_every_stock_places_its_labels(stock_id):
    """R-1404: every label of a full sheet lies on the page, and no two overlap."""
    stock = stocks()[stock_id]
    page_w, page_h = stock.page_size
    places = positions(stock, stock.per_sheet)
    assert len(places) == stock.per_sheet and {p.page for p in places} == {0}
    for p in places:
        assert 0 <= p.x and p.x + p.w <= page_w + 1e-6, (stock_id, p)
        assert 0 <= p.y and p.y + p.h <= page_h + 1e-6, (stock_id, p)
    for i, a in enumerate(places):
        for b in places[i + 1:]:
            apart = a.x + a.w <= b.x + 1e-6 or b.x + b.w <= a.x + 1e-6 or a.y + a.h <= b.y + 1e-6 \
                or b.y + b.h <= a.y + 1e-6
            assert apart, (stock_id, a, b)


def test_the_layouts_add_up():
    """The sums dossier 16 checked: the grid spans what its maker says, and the plain grids are centred."""
    s = stocks()
    misl = s["divbio-misl-1000"]
    # 7.11 + 7 x 25.40 + 22.225 (0.875 in); the dossier's 207.26 mm used the Word setup's 22.35 mm width
    assert misl.left + 7 * misl.pitch_x + misl.width == pytest.approx(207.135, abs=0.01)
    assert misl.top + 11 * misl.pitch_y + misl.pitch_y == pytest.approx(274.55, abs=0.01)
    herma = s["a4-25-66"]
    assert herma.left + 5 * herma.pitch_x + herma.width == pytest.approx(193.9, abs=0.01)
    for key in ("a4-plain", "letter-plain"):
        p = s[key]
        span_x = p.columns * p.width + (p.columns - 1) * (p.pitch_x - p.width)
        span_y = p.rows * p.height + (p.rows - 1) * (p.pitch_y - p.height)
        page_w, page_h = p.page_size
        assert p.left == pytest.approx((page_w - span_x) / 2, abs=0.01)
        assert p.top == pytest.approx((page_h - span_y) / 2, abs=0.01)
        assert span_x <= page_w - 20 and span_y <= page_h - 20  # inside the 10 mm margins
    assert s["a4-plain"].per_sheet == 72 and s["letter-plain"].per_sheet == 77


def test_start_offset_and_pages():
    stock = stocks()["a4-25-66"]
    places = positions(stock, 70, start=60, offset=(0.5, -0.3))
    assert places[0].index == 60 and places[0].page == 0
    assert places[6].page == 1 and places[6].index == 0  # 66 per sheet: the seventh goes on
    first = positions(stock, 1)[0]
    assert (places[6].x - first.x, places[6].y - first.y) == pytest.approx((0.5, -0.3))
    with pytest.raises(ValueError):
        positions(stock, 1, start=66)


@pytest.mark.parametrize("stock_id", sorted(stocks()))
def test_every_label_fits_its_cell(stock_id):
    """R-1405: the text and the QR (with its quiet zone) lie inside the label, and no text enters the quiet zone."""
    stock = stocks()[stock_id]
    w, h = stock.cell
    rec = record(slide={"catalogue_number": "NHMUK 1938.2.14.7"},
                 specimen={"locality_text": "Kidney Island, Falkland Islands"})
    cell = fit(rec, w, h)
    qx, qy, qw, qh = cell.qr.quiet
    assert INSET - EPS <= qx and qx + qw <= w - INSET + EPS and INSET - EPS <= qy and qy + qh <= h - INSET + EPS
    assert 11.0 - EPS <= qw <= 14.0 + EPS
    assert cell.lines, "the label carries its catalogue number and name"
    for line in cell.lines:
        top, bottom = line.top, line.baseline + 0.25 * line.size
        assert INSET - EPS <= line.x and line.x + line.width <= w - INSET + EPS, (stock_id, line.text)
        assert top >= INSET - EPS and bottom <= h - INSET + EPS, (stock_id, line.text)
        clear = line.x + line.width <= qx or line.x >= qx + qw or bottom <= qy or top >= qy + qh
        assert clear, (stock_id, line.text)
    assert cell.lines[0].text == "NHMUK 1938.2.14.7" or cell.lines[0].text.startswith("NHMUK")


def _rects(data: bytes, page: int = 0) -> list[tuple[float, float, float, float]]:
    """x, y (from the top), width and height in mm of the rectangles stroked on a page."""
    reader = PdfReader(io.BytesIO(data))
    page_h = float(reader.pages[page].mediabox.height)
    text = reader.pages[page].get_contents().get_data().decode("latin-1")
    out = []
    for x, y, w, h in re.findall(rf"({NUMBER}) ({NUMBER}) ({NUMBER}) ({NUMBER}) re\s+S", text):
        x, y, w, h = (float(v) for v in (x, y, w, h))
        out.append((x / MM, (page_h - y - h) / MM, w / MM, h / MM))
    return out


@pytest.mark.parametrize("stock_id", sorted(stocks()))
def test_the_test_page_measures_the_stock(stock_id):
    """R-1406: printed at 100 %, every outline measures the stock's label and sits at its position within 0.1 mm."""
    stock = stocks()[stock_id]
    data = sheet.test_page(stock)
    reader = PdfReader(io.BytesIO(data))
    box = reader.pages[0].mediabox
    assert (float(box.width) / MM, float(box.height) / MM) == pytest.approx(stock.page_size, abs=0.01)
    rects = _rects(data)
    assert len(rects) == stock.per_sheet
    for rect, place in zip(rects, positions(stock, stock.per_sheet), strict=True):
        assert rect[0] == pytest.approx(place.x, abs=0.1) and rect[1] == pytest.approx(place.y, abs=0.1)
        assert rect[2] == pytest.approx(stock.width, abs=0.1) and rect[3] == pytest.approx(stock.height, abs=0.1)
    assert "print at 100 %" in reader.pages[0].extract_text()


def test_a_sheet_on_stock_and_on_paper():
    rec = record()
    on_stock = sheet.render([rec] * 3, stocks()["divbio-misl-1000"], start=5)
    assert _rects(on_stock) == [], "nothing is outlined on die-cut labels"
    text = PdfReader(io.BytesIO(on_stock)).pages[0].extract_text()
    assert "LAM-0001" in text
    on_paper = sheet.render([rec] * 80, stocks()["a4-plain"])
    reader = PdfReader(io.BytesIO(on_paper))
    assert len(reader.pages) == 2 and len(_rects(on_paper, 0)) == 72 and len(_rects(on_paper, 1)) == 8
    assert "cut along the dashed lines" in reader.pages[0].extract_text()
    assert on_paper == sheet.render([rec] * 80, stocks()["a4-plain"]), "the same labels give the same bytes"
    with pytest.raises(ValueError):
        sheet.render([], stocks()["a4-plain"])
