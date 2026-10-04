"""The slide as primitives in millimetres, the one geometry the screen and the print share (R-1101).

Coordinates run from the slide's top-left corner, x along the long side (the slide always lies long side across,
label end on the left) and y down. The layout holds:

- the glass at the format's size, and the coverslip at its recorded size centred on the glass between the labels;
- the mount window: the slide's overview photograph, else the specimen's macro, else the first micro asset, drawn
  inside the coverslip (or the free glass) without being stretched;
- the label on the frosted end (20 mm on a slide of 70 mm or more, else 0.3 of the long side): the collection's hue
  band, the catalogue number (or the short id), the name with its epithets in italic and its authorship roman, and
  the QR with four modules of paper around it, which no text may enter (R-1102);
- the data label on the other end when the glass beside the coverslip is at least 15 mm wide, as museums label
  slides: the type status, the preparation and stain, the locality and country, the date written the collections'
  way (31.VIII.1962), the collector (leg.) and the preparer (prep.); without that room its lines follow the name on
  the frosted end while they fit, and the QR shrinks to no less than 12 mm.

Text is Courier Prime, whose advance is 0.6 em for every character, so the lines are wrapped here exactly and the SVG
and the PDF set the same lines.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from app.collections import places, vocab
from app.contracts import catalog as c
from app.delivery.iiif import best_fit

PT_MM = 25.4 / 72
ADVANCE_EM = 0.6
LINE = 1.18
MARGIN = 1.0
BAND = 1.5
NAME_PT = 5.5
DATA_PT = 5.0
QR_MM = 14.0
QR_MIN_MM = 12.0
DATA_LABEL_MIN = 15.0
ITALIC_WORDS = {"genus": 1, "subgenus": 1, "section": 1, "species": 2, "subspecies": 3, "variety": 3, "form": 3}
MARKERS = {"subsp.", "ssp.", "var.", "f.", "forma", "subvar."}
ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")


@dataclass(frozen=True)
class Run:
    text: str
    style: str = "regular"  # regular, italic, bold


@dataclass(frozen=True)
class Line:
    x: float
    baseline: float
    size: float  # the em, in mm
    runs: tuple[Run, ...]
    tone: str = "ink"  # ink, muted, type
    role: str = "text"

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)

    @property
    def width(self) -> float:
        return len(self.text) * ADVANCE_EM * self.size

    @property
    def top(self) -> float:
        # Courier Prime's ascender: 0.8 em above the baseline is enough for capitals and accents.
        return self.baseline - 0.8 * self.size


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float
    role: str  # glass, label, band, coverslip


@dataclass(frozen=True)
class Mount:
    x: float
    y: float
    w: float
    h: float
    href: str
    #: The photograph is turned a quarter turn: its orientation differs from the window's (a slide photographed
    #: standing up, shown lying down).
    turned: bool = False


@dataclass(frozen=True)
class Qr:
    x: float  # the symbol's top-left corner, the quiet zone outside it
    y: float
    module: float
    modules: tuple[tuple[bool, ...], ...]
    payload: str

    @property
    def side(self) -> float:
        return self.module * len(self.modules)

    @property
    def quiet(self) -> tuple[float, float, float, float]:
        """The quiet zone's outer box: x, y, w, h."""
        pad = 4 * self.module
        return (self.x - pad, self.y - pad, self.side + 2 * pad, self.side + 2 * pad)


@dataclass
class Layout:
    slide_id: str
    long: float
    short: float
    height: float
    collection: str
    boxes: list[Box] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    mount: Mount | None = None
    qr: Qr | None = None
    assumed: bool = False
    title: str = ""


def label_width(long: float) -> float:
    return 20.0 if long >= 70 else round(long * 0.3, 1)


def name_runs(anchor: c.AnchorRecord) -> list[Run]:
    words = anchor.name.split()
    wanted = ITALIC_WORDS.get((anchor.rank or "").lower(), 0) if anchor.kind == "taxon" else 0
    if not wanted:
        return [Run(anchor.name)]
    runs: list[Run] = []
    epithets = i = 0
    while i < len(words) and epithets < wanted:
        word = words[i]
        marker = word.lower() in MARKERS
        if not marker and epithets and not re.match(r"[a-z×-]", word):
            break
        runs.append(Run(word, "regular" if marker else "italic"))
        epithets += 0 if marker else 1
        i += 1
    if i < len(words):
        runs.append(Run(" ".join(words[i:])))
    return runs


def collections_date(value: str | None) -> str | None:
    """A date the way collection labels write it: 31.VIII.1962, VIII.1962 or 1962."""
    if not value:
        return None
    parts = value.split("-")
    if len(parts) == 3:
        return f"{int(parts[2])}.{ROMAN[int(parts[1]) - 1]}.{parts[0]}"
    if len(parts) == 2:
        return f"{ROMAN[int(parts[1]) - 1]}.{parts[0]}"
    return parts[0]


def _words(runs: list[Run]) -> list[Run]:
    out = []
    for run in runs:
        for word in run.text.split():
            out.append(Run(word, run.style))
    return out


def _pieces(word: str, width: int) -> list[str]:
    """A word too long for a line, broken where a label would break it: between letters and digits and after
    punctuation, else at the line's width."""
    parts = [p for p in re.split(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])|(?<=[-./:_])", word) if p]
    out: list[str] = []
    for part in parts:
        while len(part) > width:
            # A run of letters breaks with a hyphen; digits and codes break bare.
            cut = width - 1 if part[: width - 1].isalpha() and part[width - 1].isalpha() else width
            out.append(part[:cut] + ("-" if cut < width else ""))
            part = part[cut:]
        if out and len(out[-1]) + len(part) <= width:
            out[-1] += part
        else:
            out.append(part)
    return out


def wrap(runs: list[Run], width: int, max_lines: int) -> list[tuple[Run, ...]]:
    """Greedy wrapping of styled words into lines of at most ``width`` characters; the last line kept ends with an
    ellipsis when text is left over."""
    lines: list[list[Run]] = []
    current: list[Run] = []
    used = 0
    for word in _words(runs):
        for piece in _pieces(word.text, width) if len(word.text) > width else [word.text]:
            need = len(piece) + (1 if current else 0)
            if current and used + need > width:
                lines.append(current)
                current, used = [], 0
                need = len(piece)
            current.append(Run((" " if current else "") + piece, word.style))
            used += need
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        kept = lines[:max_lines]
        last = kept[-1]
        text = "".join(r.text for r in last)
        if len(text) >= width:
            trimmed, drop = [], len(text) - (width - 1)
            for run in reversed(last):
                if drop >= len(run.text):
                    drop -= len(run.text)
                    continue
                trimmed.insert(0, Run(run.text[: len(run.text) - drop], run.style))
                drop = 0
            last = trimmed
        kept[-1] = [*last, Run("…", last[-1].style if last else "regular")]
        lines = kept
    return [tuple(line) for line in lines]


def _data_runs(record: c.SlideRecord, lang: str) -> list[tuple[list[Run], str]]:
    """The data label's entries, each a list of runs and a tone."""
    label = record.label
    entries: list[tuple[list[Run], str]] = []
    if label.type_status:
        entries.append(([Run(label.type_status.upper(), "bold")], "type"))
    prep = vocab.load().preparations.get(label.preparation)
    prep_name = prep[lang] if prep else label.preparation
    entries.append(([Run(", ".join(p for p in (prep_name, label.stain) if p))], "ink"))
    country = record.place.country
    locality = label.locality_text or record.place.locality_text
    country_name = places.name(country, lang) if country and places.known(country) else None
    parts = [locality] if locality else []
    # The country is added unless the locality already names it ("Kidney Island, Falkland Islands").
    if country_name and not (locality and country_name.casefold() in locality.casefold()):
        parts.append(country_name)
    where = ", ".join(parts)
    if where:
        entries.append(([Run(where)], "ink"))
    when = collections_date(label.collected_on)
    if when:
        entries.append(([Run(when)], "ink"))
    if label.collector:
        entries.append(([Run(f"leg. {label.collector}")], "muted"))
    if label.preparer:
        entries.append(([Run(f"prep. {label.preparer}")], "muted"))
    return entries


def _mount_asset(record: c.SlideRecord) -> c.AssetRecord | None:
    ready = [a for a in record.assets if a.status == "ready"]
    order = [lambda a: a.family == "macro" and a.role == "slide_overview",
             lambda a: a.family == "macro" and a.role == "specimen",
             lambda a: a.family == "micro"]
    for test in order:
        for asset in ready:
            if test(asset) and (asset.media.iiif_info_url or asset.media.image_url):
                return asset
    return None


def _href(asset: c.AssetRecord) -> str:
    media = asset.media
    if media.iiif_info_url:
        size = best_fit(800, media.width_px, media.height_px)
        return media.iiif_info_url.removesuffix("/info.json") + f"/full/{size}/0/default.jpg"
    return media.image_url or ""


def _place_lines(entries: list[tuple[list[Run], str]], x: float, y0: float, y1: float, width_mm: float,
                 size: float) -> tuple[list[Line], float]:
    """Set entries as lines from ``y0`` while they fit above ``y1``; returns the lines and where the next would go."""
    chars = max(1, math.floor(width_mm / (ADVANCE_EM * size)))
    step = LINE * size
    out: list[Line] = []
    baseline = y0 + 0.8 * size
    for runs, tone in entries:
        # A line fits while its descender (0.25 em below the baseline) stays above y1.
        bottom = baseline + 0.25 * size
        room = math.floor((y1 - bottom) / step) + 1 if bottom <= y1 else 0
        if room <= 0:
            break
        for line_runs in wrap(runs, chars, room):
            out.append(Line(x, round(baseline, 3), size, line_runs, tone))
            baseline += step
    return out, baseline - 0.8 * size


def slide_layout(record: c.SlideRecord, lang: str = "en") -> Layout:
    long = max(record.format.width_mm, record.format.height_mm)
    short = min(record.format.width_mm, record.format.height_mm)
    collection = ".".join(record.placement.node.split(".")[:2])
    lay = Layout(slide_id=record.id, long=long, short=short, height=short, collection=collection,
                 assumed=record.format.assumed, title=record.label.name)
    lw = label_width(long)
    lay.boxes.append(Box(0, 0, long, short, "glass"))

    # Where the coverslip goes decides whether a data label fits on the other end.
    cover = record.coverslip
    cover_long = min(cover.long_mm, long - lw - 2) if cover else 0.0
    cover_short = min(cover.short_mm, short - 2) if cover else 0.0
    beside = (long - lw - cover_long) / 2 if cover else (long - lw) / 2 - 12
    rw = min(20.0, round(beside - 1.0, 1)) if beside - 1.0 >= DATA_LABEL_MIN else 0.0

    # The frosted end: band, catalogue number, name, then the QR at the bottom.
    lay.boxes.append(Box(0, 0, lw, short, "label"))
    lay.boxes.append(Box(0, 0, lw, BAND, "band"))
    entries_left: list[tuple[list[Run], str]] = [
        ([Run(record.label.catalogue_number or record.id, "bold")], "ink"),
        (name_runs(record.anchor), "ink"),
    ]
    data = _data_runs(record, lang)
    symbol_rows = qr_symbol(record.qr_payload)
    count = len(symbol_rows)
    text_top = BAND + 0.9
    inner = lw - 2 * MARGIN

    def qr_at(total: float) -> Qr:
        module = total / (count + 8)
        x = (lw - count * module) / 2
        y = short - 0.4 - 4 * module - count * module
        return Qr(round(x, 4), round(y, 4), module, symbol_rows, record.qr_payload)

    total = min(QR_MM, lw - 0.6)
    qr = qr_at(total)
    lines, _ = _place_lines(entries_left, MARGIN, text_top, qr.quiet[1] - 0.2, inner, NAME_PT * PT_MM)
    if not rw and data:
        # No data label: let the QR shrink to its floor to make room for the data lines under the name.
        total = max(QR_MIN_MM, min(total, lw - 0.6))
        while total > QR_MIN_MM:
            probe = qr_at(total - 0.5)
            more, _ = _place_lines(entries_left + data, MARGIN, text_top, probe.quiet[1] - 0.2, inner,
                                   NAME_PT * PT_MM)
            if len(more) <= len(lines):
                break
            total -= 0.5
        qr = qr_at(total)
        lines, _ = _place_lines(entries_left + data, MARGIN, text_top, qr.quiet[1] - 0.2, inner, NAME_PT * PT_MM)
    lay.lines.extend(lines)
    lay.qr = qr

    # The data label on the other end.
    if rw:
        x0 = long - rw
        lay.boxes.append(Box(x0, 0, rw, short, "label"))
        more, _ = _place_lines(data, x0 + MARGIN, MARGIN + 0.4, short - MARGIN, rw - 2 * MARGIN, DATA_PT * PT_MM)
        lay.lines.extend(more)

    # The mount window: inside the coverslip, or the glass between the labels.
    free_x0, free_x1 = lw, long - rw
    if cover:
        cx = (free_x0 + free_x1) / 2
        box = Box(round(cx - cover_long / 2, 4), round((short - cover_short) / 2, 4), cover_long, cover_short,
                  "coverslip")
        lay.boxes.append(box)
        window = (box.x + 0.5, box.y + 0.5, box.w - 1, box.h - 1)
    else:
        window = (free_x0 + 2, 2, free_x1 - free_x0 - 4, short - 4)
    asset = _mount_asset(record)
    if asset:
        w, h = asset.media.width_px, asset.media.height_px
        turned = bool(w and h and (h > w) != (window[3] > window[2]))
        lay.mount = Mount(*window, href=_href(asset), turned=turned)

    if lay.assumed:
        note = {"en": "Format assumed: the source does not record the slide.",
                "es": "Formato supuesto: la fuente no registra la preparación."}[lang]
        size = round(min(2.4, (long - 1) / (len(note) * ADVANCE_EM)), 3)
        lay.lines.append(Line(0, short + 1.2 + size, size, (Run(note, "italic"),), "muted", role="note"))
        lay.height = short + 1.8 + 1.25 * size
    return lay


def qr_symbol(payload: str) -> tuple[tuple[bool, ...], ...]:
    from app.labels.qr import symbol

    return symbol(payload).modules
