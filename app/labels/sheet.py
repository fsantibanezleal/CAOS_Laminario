"""A sheet of slide labels on a label stock, and its test page (U14, R-1404 to R-1406).

Labels are placed from the stock's record (``stocks.py``), from a start position and moved by a printer offset, and
each holds U11's label fitted to it (``cell.py``). On die-cut stock nothing is drawn outside the labels and no outline
is drawn at all (it would print on the labels); on plain paper each label is framed by a dashed cut line. The test
page draws every label's outline at the stock's own size and position, with the instruction to print it at 100 % on
plain paper and hold it against a sheet of the stock (Diversified Biotech's instruction, dossier 16).

Drawn with reportlab in points, with the same faces, colours and QR matrix as the slide's own sheet (``pdf.py``); the
output is reproducible.
"""

from __future__ import annotations

import io

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from app.contracts import catalog as c
from app.labels.cell import Cell, fit
from app.labels.layout import ADVANCE_EM
from app.labels.pdf import FACES, MM, PRINT, _register
from app.labels.stocks import Stock, positions

MAX_SLIDES = 500


def _draw_cell(pdf: canvas.Canvas, cell: Cell, left: float, top: float, page_h: float) -> None:
    def X(x: float) -> float:
        return (left + x) * MM

    def Y(y: float) -> float:
        return page_h - (top + y) * MM

    for box in cell.boxes:
        if box.role == "band":
            pdf.setFillColor(HexColor(PRINT["hues"].get(cell.collection, PRINT["ink"])))
            pdf.rect(X(box.x), Y(box.y + box.h), box.w * MM, box.h * MM, stroke=0, fill=1)
    tones = {"ink": HexColor(PRINT["ink"]), "muted": HexColor(PRINT["muted"]), "type": HexColor(PRINT["type"])}
    for line in cell.lines:
        pdf.setFillColor(tones[line.tone])
        x = line.x
        for run in line.runs:
            pdf.setFont(FACES[run.style], line.size * MM)
            pdf.drawString(X(x), Y(line.baseline), run.text)
            x += len(run.text) * ADVANCE_EM * line.size
    if cell.qr:
        qr = cell.qr
        pdf.setFillColor(HexColor(PRINT["ink"]))
        path = pdf.beginPath()
        for r, row in enumerate(qr.modules):
            col = 0
            while col < len(row):
                if row[col]:
                    start = col
                    while col < len(row) and row[col]:
                        col += 1
                    path.rect(X(qr.x + start * qr.module), Y(qr.y + (r + 1) * qr.module),
                              (col - start) * qr.module * MM, qr.module * MM)
                else:
                    col += 1
        pdf.drawPath(path, stroke=0, fill=1)


def _new(stock: Stock, title: str) -> tuple[canvas.Canvas, io.BytesIO, float]:
    _register()
    out = io.BytesIO()
    page_w, page_h = (v * MM for v in stock.page_size)
    pdf = canvas.Canvas(out, pagesize=(page_w, page_h), invariant=1, pageCompression=1)
    pdf.setTitle(title)
    pdf.setAuthor("Laminario")
    pdf.setSubject(f"Slide labels on {stock.name}")
    return pdf, out, page_h


# The line at a page's foot, in the sheet's language.
FOOTERS = {
    "sheet": {"en": "Laminario, {name}: print at 100 %, cut along the dashed lines",
              "es": "Laminario, {name}: imprima al 100 %, corte por las líneas discontinuas"},
    "test": {"en": "Laminario test page, {name}: print at 100 % on plain paper and hold it against a sheet of the "
                   "labels",
             "es": "Página de prueba de Laminario, {name}: imprima al 100 % en papel común y sosténgala contra un "
                   "pliego de etiquetas"},
}


def _words(which: str, stock: Stock, lang: str) -> str:
    lang = lang if lang in ("en", "es") else "en"
    return FOOTERS[which][lang].format(name=stock.name_es if lang == "es" else stock.name)


def _footer(pdf: canvas.Canvas, stock: Stock, page_h: float, text: str) -> None:
    pdf.setFillColor(HexColor(PRINT["muted"]))
    pdf.setFont(FACES["regular"], 7)
    pdf.drawString(10 * MM, page_h - (stock.page_size[1] - 5) * MM, text)


def render(records: list[c.SlideRecord], stock: Stock, start: int = 0, offset: tuple[float, float] = (0.0, 0.0),
           lang: str = "en") -> bytes:
    """The labels of ``records`` in order, from ``start``, moved by ``offset`` (x, y in mm)."""
    if not records:
        raise ValueError("no slides to label")
    if len(records) > MAX_SLIDES:
        raise ValueError(f"at most {MAX_SLIDES} slides per sheet")
    width, height = stock.cell
    cells = [fit(r, width, height, lang) for r in records]
    places = positions(stock, len(cells), start, offset)
    pdf, out, page_h = _new(stock, f"Laminario labels ({len(cells)})")
    page = 0
    for cell, place in zip(cells, places, strict=True):
        if place.page != page:
            if stock.kind == "plain":
                _footer(pdf, stock, page_h, _words("sheet", stock, lang))
            pdf.showPage()
            page = place.page
        if stock.kind == "plain":
            pdf.setStrokeColor(HexColor(PRINT["edge"]))
            pdf.setLineWidth(0.2)
            pdf.setDash(1.2 * MM, 0.8 * MM)
            pdf.rect(place.x * MM, page_h - (place.y + place.h) * MM, place.w * MM, place.h * MM, stroke=1, fill=0)
            pdf.setDash()
        _draw_cell(pdf, cell, place.x, place.y, page_h)
    if stock.kind == "plain":
        _footer(pdf, stock, page_h, _words("sheet", stock, lang))
    pdf.showPage()
    pdf.save()
    return out.getvalue()


def test_page(stock: Stock, offset: tuple[float, float] = (0.0, 0.0), lang: str = "en") -> bytes:
    """Every label's outline at the stock's own size and position, moved by ``offset``, on one page."""
    pdf, out, page_h = _new(stock, f"Laminario test page: {stock.name}")
    pdf.setStrokeColor(HexColor(PRINT["ink"]))
    pdf.setLineWidth(0.25)
    for place in positions(stock, stock.per_sheet, 0, offset):
        pdf.rect(place.x * MM, page_h - (place.y + stock.height) * MM, stock.width * MM, stock.height * MM,
                 stroke=1, fill=0)
    _footer(pdf, stock, page_h, _words("test", stock, lang))
    pdf.showPage()
    pdf.save()
    return out.getvalue()
