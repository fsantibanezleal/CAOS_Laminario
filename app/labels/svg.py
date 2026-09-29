"""The slide's layout as SVG in millimetres, for the screen.

Inlined by the slide place (``standalone=False``), it carries only class names and takes its colours from the page's
tokens: the paper of the labels, the glass, the collection's hue, so it changes with the room. Served on its own
(``standalone=True``, a download), it carries the daylight colours in its own stylesheet. The text is Courier Prime,
the page's label face; ids are prefixed with the slide's short id, so several slides can share a page.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from app.labels.layout import Layout, Line

PRINT = json.loads((Path(__file__).parent / "print-colours.json").read_text(encoding="utf-8"))
FACE = "'Courier Prime', 'Courier New', monospace"


def _n(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _style() -> str:
    return (
        "<style>"
        f".lam-glass{{fill:#eef1f1;fill-opacity:.55}}.lam-edge{{fill:none;stroke:{PRINT['edge']};stroke-width:.25}}"
        f".lam-paper{{fill:{PRINT['paper']}}}.lam-cover{{fill:#ffffff;fill-opacity:.25;stroke:{PRINT['edge']};"
        "stroke-width:.15;stroke-dasharray:.8 .6}"
        f".lam-ink{{fill:{PRINT['ink']}}}.lam-muted{{fill:{PRINT['muted']}}}.lam-type{{fill:{PRINT['type']}}}"
        f".lam-qr{{fill:{PRINT['ink']}}}.lam-note{{fill:{PRINT['muted']}}}"
        "</style>"
    )


def _text(line: Line) -> str:
    tone = "note" if line.role == "note" else line.tone
    spans = []
    for run in line.runs:
        attrs = ' font-style="italic"' if run.style == "italic" else ' font-weight="700"' if run.style == "bold" else ""
        spans.append(f"<tspan{attrs}>{escape(run.text)}</tspan>")
    return (f'<text class="lam-{tone}" x="{_n(line.x)}" y="{_n(line.baseline)}" font-size="{_n(line.size)}" '
            f'font-family="{FACE}" xml:space="preserve">{"".join(spans)}</text>')


def _qr_path(lay: Layout) -> str:
    qr = lay.qr
    parts = []
    for r, row in enumerate(qr.modules):
        c = 0
        while c < len(row):
            if row[c]:
                start = c
                while c < len(row) and row[c]:
                    c += 1
                x, y, w = qr.x + start * qr.module, qr.y + r * qr.module, (c - start) * qr.module
                parts.append(f"M{_n(x)} {_n(y)}h{_n(w)}v{_n(qr.module)}h{_n(-w)}z")
            else:
                c += 1
    return f'<path class="lam-qr" d="{"".join(parts)}"/>'


def render(lay: Layout, standalone: bool = True) -> str:
    sid = lay.slide_id
    hue = PRINT["hues"].get(lay.collection, PRINT["ink"])
    slug = lay.collection.split(".")[-1]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_n(lay.long)} {_n(lay.height)}" '
        f'width="{_n(lay.long)}mm" height="{_n(lay.height)}mm" role="img" aria-labelledby="{sid}-title" '
        f'data-slide="{sid}" data-format="{_n(lay.long)}x{_n(lay.short)}" '
        f'style="--band: var(--h-{slug}, {hue})">',
        f'<title id="{sid}-title">{escape(lay.title)}</title>',
    ]
    if standalone:
        out.append(_style())
    glass = next(b for b in lay.boxes if b.role == "glass")
    out.append(f'<rect class="lam-glass" x="0" y="0" width="{_n(glass.w)}" height="{_n(glass.h)}" rx=".5"/>')
    if lay.mount:
        m = lay.mount
        out.append(f'<clipPath id="{sid}-mount"><rect x="{_n(m.x)}" y="{_n(m.y)}" width="{_n(m.w)}" '
                   f'height="{_n(m.h)}"/></clipPath>')
        out.append(f'<image class="lam-mount" href={quoteattr(m.href)} x="{_n(m.x)}" y="{_n(m.y)}" width="{_n(m.w)}" '
                   f'height="{_n(m.h)}" preserveAspectRatio="xMidYMid meet" clip-path="url(#{sid}-mount)"/>')
    for box in lay.boxes:
        if box.role == "coverslip":
            out.append(f'<rect class="lam-cover" x="{_n(box.x)}" y="{_n(box.y)}" width="{_n(box.w)}" '
                       f'height="{_n(box.h)}" rx=".2"/>')
    for box in lay.boxes:
        if box.role == "label":
            out.append(f'<rect class="lam-paper" x="{_n(box.x)}" y="{_n(box.y)}" width="{_n(box.w)}" '
                       f'height="{_n(box.h)}"/>')
    for box in lay.boxes:
        if box.role == "band":
            out.append(f'<rect class="lam-band" x="{_n(box.x)}" y="{_n(box.y)}" width="{_n(box.w)}" '
                       f'height="{_n(box.h)}" fill="{hue}"/>')
    out.extend(_text(line) for line in lay.lines)
    if lay.qr:
        out.append(_qr_path(lay))
    out.append(f'<rect class="lam-edge" x="0" y="0" width="{_n(glass.w)}" height="{_n(glass.h)}" rx=".5"/>')
    out.append("</svg>")
    return "\n".join(out) + "\n"
