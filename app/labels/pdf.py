"""The slide's labels on paper, at 1:1 (R-083).

An A4 sheet, one slide per block: the slide's outline at its format's size, so a print at 100 % can be checked with a
ruler; the labels as cut lines with their text and QR, to be printed on label paper, cut out and stuck on the physical
slide, so it carries the same QR as its digital twin; the coverslip's place dotted, to position the labels; a cut
mark at each corner; and under the block the permalink and the size the outline must measure. The mount photograph
is not printed: the physical slide has its specimen.

Drawn with reportlab in points (72 / 25.4 per millimetre), with Courier Prime embedded (the SIL Open Font License
permits embedding a font in a document), from the same layout and the same QR matrix as the screen (R-1101, R-1103).
The output is reproducible (``invariant``): the same slide gives the same bytes.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.labels.layout import ADVANCE_EM, Layout

HERE = Path(__file__).parent
PRINT = json.loads((HERE / "print-colours.json").read_text(encoding="utf-8"))
MM = 72 / 25.4
PAGE_MARGIN = 20.0
FACES = {"regular": "LaminarioLabel", "italic": "LaminarioLabel-Italic", "bold": "LaminarioLabel-Bold"}
_registered = False


def _register() -> None:
    global _registered
    if _registered:
        return
    for style, name in FACES.items():
        pdfmetrics.registerFont(TTFont(name, str(HERE / "fonts" / f"courier-prime-{style}.ttf")))
    _registered = True


def _draw(pdf: canvas.Canvas, lay: Layout, left: float, top: float, page_h: float, permalink: str) -> float:
    """Draw one slide block with its top-left corner at (left, top) mm from the page's top-left; returns its height."""

    def X(x: float) -> float:
        return (left + x) * MM

    def Y(y: float) -> float:
        return page_h - (top + y) * MM

    ink = HexColor(PRINT["ink"])
    edge = HexColor(PRINT["edge"])
    # The slide's outline, at its format's size: the rectangle the print is measured by.
    pdf.setStrokeColor(edge)
    pdf.setLineWidth(0.3)
    pdf.rect(X(0), Y(lay.short), lay.long * MM, lay.short * MM, stroke=1, fill=0)
    # Cut marks at the corners, 1 mm away from the outline, 4 mm long.
    for cx, cy, dx, dy in ((0, 0, -1, -1), (lay.long, 0, 1, -1), (0, lay.short, -1, 1), (lay.long, lay.short, 1, 1)):
        pdf.line(X(cx + dx * 1), Y(cy), X(cx + dx * 5), Y(cy))
        pdf.line(X(cx), Y(cy + dy * 1), X(cx), Y(cy + dy * 5))
    pdf.setDash(0.8 * MM, 0.6 * MM)
    for box in lay.boxes:
        if box.role == "coverslip":
            pdf.rect(X(box.x), Y(box.y + box.h), box.w * MM, box.h * MM, stroke=1, fill=0)
    pdf.setDash()
    for box in lay.boxes:
        if box.role == "label":
            pdf.setLineWidth(0.2)
            pdf.setDash(1.2 * MM, 0.8 * MM)
            pdf.rect(X(box.x), Y(box.y + box.h), box.w * MM, box.h * MM, stroke=1, fill=0)
            pdf.setDash()
        if box.role == "band":
            pdf.setFillColor(HexColor(PRINT["hues"].get(lay.collection, PRINT["ink"])))
            pdf.rect(X(box.x), Y(box.y + box.h), box.w * MM, box.h * MM, stroke=0, fill=1)
    tones = {"ink": ink, "muted": HexColor(PRINT["muted"]), "type": HexColor(PRINT["type"])}
    for line in lay.lines:
        if line.role == "note":
            continue
        pdf.setFillColor(tones[line.tone])
        size_pt = line.size * MM
        x = line.x
        for run in line.runs:
            pdf.setFont(FACES[run.style], size_pt)
            pdf.drawString(X(x), Y(line.baseline), run.text)
            x += len(run.text) * ADVANCE_EM * line.size
    if lay.qr:
        # One path for every dark module, filled once: separate fills leave anti-aliased seams between rows.
        qr = lay.qr
        pdf.setFillColor(ink)
        path = pdf.beginPath()
        for r, row in enumerate(qr.modules):
            c = 0
            while c < len(row):
                if row[c]:
                    start = c
                    while c < len(row) and row[c]:
                        c += 1
                    y = qr.y + (r + 1) * qr.module
                    path.rect(X(qr.x + start * qr.module), Y(y), (c - start) * qr.module * MM, qr.module * MM)
                else:
                    c += 1
        pdf.drawPath(path, stroke=0, fill=1)
    pdf.setFillColor(HexColor(PRINT["muted"]))
    pdf.setFont(FACES["regular"], 7)
    size = f"{lay.long:g} x {lay.short:g} mm"
    note = next((ln.text for ln in lay.lines if ln.role == "note"), "")
    pdf.drawString(X(0), Y(lay.short + 9), f"{permalink}   print at 100 %: the outline measures {size}")
    if note:
        pdf.drawString(X(0), Y(lay.short + 12.5), note)
    return lay.short + 16


def render(layouts: list[tuple[Layout, str]], title: str) -> bytes:
    """The sheet for one or more slides, each with its permalink; a slide that does not fit the page starts a new
    page."""
    _register()
    out = io.BytesIO()
    page_w, page_h = A4
    pdf = canvas.Canvas(out, pagesize=A4, invariant=1, pageCompression=1)
    pdf.setTitle(title)
    pdf.setAuthor("Laminario")
    pdf.setSubject("Slide labels at 1:1")
    top = PAGE_MARGIN
    for lay, permalink in layouts:
        needed = lay.short + 16
        if top + needed > page_h / MM - PAGE_MARGIN:
            pdf.showPage()
            top = PAGE_MARGIN
        top += _draw(pdf, lay, PAGE_MARGIN + 6, top + 6, page_h, permalink)
    pdf.showPage()
    pdf.save()
    return out.getvalue()
