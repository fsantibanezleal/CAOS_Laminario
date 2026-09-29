"""Label stocks as data (U14, R-1404): where each label of a sheet lies.

``stocks.yaml`` holds each stock's page, label size, columns and rows, margins and pitches, with the source of the
numbers. ``positions`` gives every label's rectangle on a page, in millimetres from the page's top-left corner, for a
start position and a printer offset; the sheet renderer draws inside them.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).parent
PAGES = {"A4": (210.0, 297.0), "Letter": (215.9, 279.4)}


@dataclass(frozen=True)
class Stock:
    id: str
    name: str  # in English
    name_es: str
    kind: str  # plain or stock
    page: str
    width: float
    height: float
    columns: int
    rows: int
    top: float
    left: float
    pitch_x: float
    pitch_y: float
    radius: float
    source: str
    warnings: tuple[str, ...]

    @property
    def page_size(self) -> tuple[float, float]:
        return PAGES[self.page]

    @property
    def per_sheet(self) -> int:
        return self.columns * self.rows

    @property
    def cell(self) -> tuple[float, float]:
        """The rectangle a label is drawn within: its size, or the pitch where the rows or columns are closer."""
        return min(self.width, self.pitch_x), min(self.height, self.pitch_y)


@dataclass(frozen=True)
class Place:
    page: int
    index: int  # on its page
    x: float
    y: float
    w: float
    h: float


@lru_cache
def stocks() -> dict[str, Stock]:
    raw = yaml.safe_load((HERE / "stocks.yaml").read_text(encoding="utf-8"))
    out = {}
    for key, s in raw.items():
        names = s["name"] if isinstance(s["name"], dict) else {"en": s["name"], "es": s["name"]}
        out[key] = Stock(id=key, name=names["en"], name_es=names["es"], kind=s["kind"], page=s["page"],
                         width=float(s["label"][0]),
                         height=float(s["label"][1]), columns=int(s["grid"][0]), rows=int(s["grid"][1]),
                         top=float(s["margin"][0]), left=float(s["margin"][1]), pitch_x=float(s["pitch"][0]),
                         pitch_y=float(s["pitch"][1]), radius=float(s.get("radius", 0)), source=s["source"],
                         warnings=tuple(s.get("warnings", ())))
    return out


def positions(stock: Stock, count: int, start: int = 0, offset: tuple[float, float] = (0.0, 0.0)) -> list[Place]:
    """Where ``count`` labels go, row by row from position ``start`` (0-based) of the first page, moved by the
    printer ``offset`` (x, y in mm); a sheet that fills goes on to the next page from its first position."""
    if not 0 <= start < stock.per_sheet:
        raise ValueError(f"the start position is 0 to {stock.per_sheet - 1}")
    w, h = stock.cell
    out: list[Place] = []
    slot = start
    page = 0
    for _ in range(count):
        if slot == stock.per_sheet:
            slot, page = 0, page + 1
        row, column = divmod(slot, stock.columns)
        out.append(Place(page, slot, stock.left + column * stock.pitch_x + offset[0],
                         stock.top + row * stock.pitch_y + offset[1], w, h))
        slot += 1
    return out
