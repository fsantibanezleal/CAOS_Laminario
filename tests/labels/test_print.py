"""R-083: printed at 100 %, the slide on the sheet measures its format within 0.1 mm."""

from __future__ import annotations

import io
import re

import pytest
from pypdf import PdfReader

from app.labels import pdf
from app.labels.layout import slide_layout
from app.labels.pdf import MM
from tests.labels.support import record

NUMBER = r"-?(?:\d+(?:\.\d*)?|\.\d+)"  # reportlab writes .919345


def _stroked_rects(data: bytes) -> list[tuple[float, float]]:
    """Widths and heights, in mm, of the rectangles stroked on the first page (the outline, labels, coverslip)."""
    page = PdfReader(io.BytesIO(data)).pages[0]
    text = page.get_contents().get_data().decode("latin-1")
    return [(float(w) / MM, float(h) / MM) for _, _, w, h in re.findall(
        rf"({NUMBER}) ({NUMBER}) ({NUMBER}) ({NUMBER}) re\s+S", text)]


@pytest.mark.parametrize("fmt,size", [("iso_76x26", (76, 26)), ("us_75x25", (75, 25)), ("petro_27x46", (46, 27)),
                                      ("us_2x3in", (76.2, 50.8))])
def test_print_dimensions(fmt, size):
    rec = record(slide={"format": fmt})
    data = pdf.render([(slide_layout(rec), rec.permalink)], title="t")
    reader = PdfReader(io.BytesIO(data))
    box = reader.pages[0].mediabox
    assert (float(box.width) / MM, float(box.height) / MM) == pytest.approx((210, 297), abs=0.01)  # A4
    outline = _stroked_rects(data)[0]
    assert abs(outline[0] - size[0]) <= 0.1 and abs(outline[1] - size[1]) <= 0.1, outline
    words = reader.pages[0].extract_text()
    assert rec.permalink in words and f"{size[0]:g} x {size[1]:g} mm" in words


def test_the_print_embeds_the_label_face_and_is_reproducible():
    rec = record(slide={"format_assumed": True})
    lay = slide_layout(rec)
    first = pdf.render([(lay, rec.permalink)], title="t")
    assert first == pdf.render([(lay, rec.permalink)], title="t")
    fonts = {f.get_object()["/BaseFont"] for f in PdfReader(io.BytesIO(first)).pages[0]["/Resources"]["/Font"].values()}
    assert {"/AAAAAA+CourierPrime-Regular", "/AAAAAA+CourierPrime-Italic", "/AAAAAA+CourierPrime-Bold"} <= fonts
    assert "assumed" in PdfReader(io.BytesIO(first)).pages[0].extract_text()


def test_many_slides_flow_onto_pages():
    rec = record()
    lay = slide_layout(rec)
    data = pdf.render([(lay, rec.permalink)] * 12, title="t")
    assert len(PdfReader(io.BytesIO(data)).pages) >= 2
