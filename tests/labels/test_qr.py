"""R-1103: the QR encodes the permalink in upper case in alphanumeric mode, and the SVG and the PDF draw the same
modules."""

from __future__ import annotations

import io
import re

from pypdf import PdfReader

from app.labels import pdf, svg
from app.labels.layout import slide_layout
from app.labels.pdf import MM, PAGE_MARGIN
from app.labels.qr import symbol
from tests.labels.support import HOST, record

NUMBER = r"-?(?:\d+(?:\.\d*)?|\.\d+)"  # reportlab writes .919345


def test_the_symbol():
    s = symbol(f"{HOST}/s/9422P6AW".upper())
    assert (s.version, s.mode, s.size) == (3, "alphanumeric", 29)


def _grid(cells: set[tuple[int, int]], size: int) -> tuple[tuple[bool, ...], ...]:
    return tuple(tuple((r, c) in cells for c in range(size)) for r in range(size))


def test_svg_and_pdf_draw_the_same_modules():
    rec = record()
    lay = slide_layout(rec)
    qr = lay.qr
    assert qr.payload == rec.qr_payload == rec.permalink.upper()

    # The SVG: one path of horizontal runs, "Mx yhWv1h-Wz".
    drawn = svg.render(lay, standalone=True)
    path = re.search(r'class="lam-qr" d="([^"]+)"', drawn).group(1)
    cells = set()
    for x, y, w in re.findall(rf"M({NUMBER}) ({NUMBER})h({NUMBER})v", path):
        col, row = round((float(x) - qr.x) / qr.module), round((float(y) - qr.y) / qr.module)
        cells |= {(row, col + k) for k in range(round(float(w) / qr.module))}
    assert _grid(cells, len(qr.modules)) == qr.modules

    # The PDF: the same runs as rectangles of one filled path, in points from the page's bottom-left.
    data = pdf.render([(lay, rec.permalink)], title="t")
    text = PdfReader(io.BytesIO(data)).pages[0].get_contents().get_data().decode("latin-1")
    left, top = PAGE_MARGIN + 6, PAGE_MARGIN + 6
    page_h = 841.8897637795275
    cells = set()
    for x, y, w, h in re.findall(rf"({NUMBER}) ({NUMBER}) ({NUMBER}) ({NUMBER}) re", text):
        w_mm, h_mm = float(w) / MM, float(h) / MM
        if abs(h_mm - qr.module) > 1e-3:
            continue
        x_mm = float(x) / MM - left
        y_top = (page_h - float(y)) / MM - top - qr.module
        col, row = round((x_mm - qr.x) / qr.module), round((y_top - qr.y) / qr.module)
        cells |= {(row, col + k) for k in range(round(w_mm / qr.module))}
    assert _grid(cells, len(qr.modules)) == qr.modules
