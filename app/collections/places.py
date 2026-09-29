"""Countries: the ISO 3166-1 vocabulary with English and Spanish names, and the country a point lies in.

The data are built by ``scripts/build_countries.py``: the names from Unicode CLDR, the shapes from Natural Earth
1:50m map units rounded to 0.01 degree (dossier 12). A specimen's country is either stated (a source that names it:
a GBIF occurrence, a museum's sheet, a label) or implied by its coordinates. A stated country and coordinates must
agree: the point lies in the country's shape or within ``TOLERANCE_DEG`` of its edge (coasts are rounded, and a
collecting point on a beach or a boat is still that country's).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
TOLERANCE_DEG = 0.25


@dataclass(frozen=True)
class Shape:
    code: str
    bbox: tuple[float, float, float, float]  # west, south, east, north
    polygons: tuple[tuple[tuple[tuple[float, float], ...], ...], ...]  # polygons of rings of (lon, lat)


@lru_cache(maxsize=1)
def countries() -> dict[str, dict[str, str]]:
    return json.loads((DATA / "vocab" / "countries.json").read_text(encoding="utf-8"))["countries"]


@lru_cache(maxsize=1)
def shapes() -> dict[str, Shape]:
    out = {}
    for f in json.loads((DATA / "countries.geojson").read_text(encoding="utf-8"))["features"]:
        coords = f["geometry"]["coordinates"]
        polys = tuple(tuple(tuple((p[0], p[1]) for p in ring) for ring in poly) for poly in coords)
        xs = [p[0] for poly in polys for p in poly[0]]
        ys = [p[1] for poly in polys for p in poly[0]]
        out[f["id"]] = Shape(f["id"], (min(xs), min(ys), max(xs), max(ys)), polys)
    return out


def known(code: str | None) -> bool:
    return code is not None and code in countries()


def name(code: str, lang: str = "en") -> str:
    return countries()[code][lang]


@lru_cache(maxsize=1)
def _by_name() -> dict[str, str]:
    return {n.casefold(): code for code, names in countries().items() for n in names.values()}


def code_of(country_name: str) -> str | None:
    """The code of a country named exactly as CLDR names it in English or Spanish ("Solomon Islands", "Kenia")."""
    return _by_name().get(country_name.strip().casefold())


def _in_ring(lon: float, lat: float, ring: tuple[tuple[float, float], ...]) -> bool:
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _in_shape(lon: float, lat: float, shape: Shape) -> bool:
    west, south, east, north = shape.bbox
    if not (west <= lon <= east and south <= lat <= north):
        return False
    for poly in shape.polygons:
        if _in_ring(lon, lat, poly[0]) and not any(_in_ring(lon, lat, hole) for hole in poly[1:]):
            return True
    return False


def _edge_distance(lon: float, lat: float, shape: Shape) -> float:
    """Distance in degrees (longitude scaled by the latitude's cosine) from the point to the shape's outer edges."""
    k = math.cos(math.radians(lat))
    best = math.inf
    for poly in shape.polygons:
        ring = poly[0]
        for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
            ax, ay, bx, by = (x1 - lon) * k, y1 - lat, (x2 - lon) * k, y2 - lat
            dx, dy = bx - ax, by - ay
            length = dx * dx + dy * dy
            t = 0.0 if length == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / length))
            best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def locate(lat: float, lon: float) -> str | None:
    """The country whose shape contains the point; else the nearest within ``TOLERANCE_DEG`` (a coastal point that
    the rounded shapes leave in the water); else none (the open sea)."""
    for shape in shapes().values():
        if _in_shape(lon, lat, shape):
            return shape.code
    pad = TOLERANCE_DEG * 2
    near = []
    for shape in shapes().values():
        west, south, east, north = shape.bbox
        if west - pad <= lon <= east + pad and south - pad <= lat <= north + pad:
            distance = _edge_distance(lon, lat, shape)
            if distance <= TOLERANCE_DEG:
                near.append((distance, shape.code))
    return min(near)[1] if near else None


def agrees(code: str, lat: float, lon: float) -> bool:
    """Whether coordinates agree with a stated country (a country without a shape at this scale cannot be checked)."""
    shape = shapes().get(code)
    if shape is None:
        return True
    west, south, east, north = shape.bbox
    pad = TOLERANCE_DEG * 2
    if not (west - pad <= lon <= east + pad and south - pad <= lat <= north + pad):
        return False
    return _in_shape(lon, lat, shape) or _edge_distance(lon, lat, shape) <= TOLERANCE_DEG
