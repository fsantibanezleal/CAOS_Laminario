"""A slide's label fitted to one label of a stock (U14, R-1405).

The content of U11's frosted-end label (``layout.py``): the collection's hue band, the catalogue number, the name with
its epithets in italic, the data lines while they fit, and the QR with its four modules of quiet zone, which no text
enters. The cell is the stock's label, less 0.8 mm on every side (printers and die-cut stocks both drift).

The QR goes at the label's foot (as on the slide's label end) or on its right, and measures 14 mm with its quiet zone,
or less, down to 11 mm (29 modules of 0.3 mm). Every arrangement and size is tried, and the label keeps the one that,
in this order: sets the catalogue number and the name complete; sets them in the fewest lines (a word split across
lines is a line more); sets the most data lines; and has the largest QR.

Coordinates are millimetres from the label's top-left corner, as the slide layout's are from the slide's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.contracts import catalog as c
from app.labels.layout import (ADVANCE_EM, BAND, NAME_PT, PT_MM, QR_MM, Box, Line, Qr, Run, _data_runs, _place_lines,
                               name_runs, qr_symbol, wrap)

INSET = 0.8
QR_FLOOR = 11.0
TEXT_PT = NAME_PT
STEP = 0.5


@dataclass
class Cell:
    width: float
    height: float
    collection: str
    boxes: list[Box] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    qr: Qr | None = None


def fit(record: c.SlideRecord, width: float, height: float, lang: str = "en") -> Cell:
    """The label's content inside a ``width`` x ``height`` mm label."""
    collection = ".".join(record.placement.node.split(".")[:2])
    x0, y0, x1, y1 = INSET, INSET, width - INSET, height - INSET
    essential = [([Run(record.label.catalogue_number or record.id, "bold")], "ink"), (name_runs(record.anchor), "ink")]
    entries = essential + _data_runs(record, lang)
    rows = qr_symbol(record.qr_payload)
    count = len(rows)
    text_top = y0 + BAND + 0.6
    size = TEXT_PT * PT_MM
    below = y1 - y0 - BAND - 0.4  # the height under the band

    def qr_of(total: float, right: bool) -> Qr:
        module = total / (count + 8)
        side = count * module
        if right:
            x = x1 - 4 * module - side
            y = y0 + BAND + 0.4 + (below - total) / 2 + 4 * module
        else:
            x = x0 + (x1 - x0 - side) / 2
            y = y1 - 4 * module - side
        return Qr(round(x, 4), round(y, 4), module, rows, record.qr_payload)

    def text_box(qr: Qr, right: bool) -> tuple[float, float, float]:
        """The text's left, bottom and width beside or above the QR's quiet zone."""
        if right:
            return x0 + 0.2, y1, qr.quiet[0] - 0.3 - (x0 + 0.2)
        return x0 + 0.2, qr.quiet[1] - 0.2, x1 - x0 - 0.4

    def needed(width_mm: float) -> int:
        chars = max(1, int(width_mm // (ADVANCE_EM * size)))
        return sum(len(wrap(runs, chars, 99)) for runs, _ in essential)

    best: tuple[tuple, Qr, list[Line]] | None = None
    for right in (False, True):
        total = min(QR_MM, x1 - x0 if not right else below, below if not right else x1 - x0)
        while total >= QR_FLOOR - 1e-9:
            qr = qr_of(total, right)
            left, bottom, width_mm = text_box(qr, right)
            if width_mm >= 4 * ADVANCE_EM * size:  # room for four characters at least
                core, _ = _place_lines(essential, left, text_top, bottom, width_mm, size)
                complete = len(core) == needed(width_mm) and not any(ln.text.endswith("…") for ln in core)
                lines, _ = _place_lines(entries, left, text_top, bottom, width_mm, size)
                score = (complete, -len(core) if complete else len(core), len(lines), total)
                if best is None or score > best[0]:
                    best = (score, qr, lines)
            total = round(total - STEP, 3)
    if best is None:
        raise ValueError(f"a {width} x {height} mm label is too small for the QR ({QR_FLOOR} mm at least)")
    cell = Cell(width, height, collection)
    cell.boxes.append(Box(x0, y0, x1 - x0, BAND, "band"))
    cell.qr, cell.lines = best[1], best[2]
    return cell
