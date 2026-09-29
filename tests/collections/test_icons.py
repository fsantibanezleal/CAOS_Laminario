"""The icon system (dossier 03, section 5): one sprite, one grid, one stroke, a frame by kind, EN and ES titles.

The source symbols are measured, not trusted: every path, circle, ellipse and rect is sampled (curves and arcs
along their length, rects at their corners after rotation) and must stay inside the frame's clear area.
"""

from __future__ import annotations

import importlib.util
import math
import re
import xml.etree.ElementTree as ET

from tests.collections.support import BUILT_SPRITE, ROOT, SOURCE_SPRITE, SVG

#: A place drawing stays within this distance of the centre: the frame circle's inner edge is 12.25.
PLACE_RADIUS = 11.25
#: A facet drawing stays inside this box: the square's inner edge is at 5.75 and 26.25.
FACET_BOX = (6.5, 25.5)
ALLOWED_ATTRIBUTES = {"d", "cx", "cy", "r", "rx", "ry", "x", "y", "width", "height", "fill", "stroke",
                      "fill-rule", "stroke-dasharray", "transform"}


def load_builder():
    spec = importlib.util.spec_from_file_location("build_icons", ROOT / "scripts" / "build_icons.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- geometry ---------------------------------------------------------------------------------------------------

TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?")
ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def _bezier(points: list[tuple[float, float]], n: int = 24) -> list[tuple[float, float]]:
    out = []
    for i in range(n + 1):
        t = i / n
        pts = points
        while len(pts) > 1:
            pts = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(pts, pts[1:], strict=False)]
        out.append(pts[0])
    return out


def _arc(p0, rx, ry, phi, large, sweep, p1, n: int = 32) -> list[tuple[float, float]]:
    """Points along an SVG elliptical arc (the endpoint-to-centre conversion of SVG 1.1, appendix F.6)."""
    if rx == 0 or ry == 0:
        return [p0, p1]
    rx, ry = abs(rx), abs(ry)
    cos, sin = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = cos * dx + sin * dy, -sin * dx + cos * dy
    scale = x1 ** 2 / rx ** 2 + y1 ** 2 / ry ** 2
    if scale > 1:
        rx, ry = rx * math.sqrt(scale), ry * math.sqrt(scale)
    num = max(rx ** 2 * ry ** 2 - rx ** 2 * y1 ** 2 - ry ** 2 * x1 ** 2, 0.0)
    coef = math.sqrt(num / (rx ** 2 * y1 ** 2 + ry ** 2 * x1 ** 2)) * (-1 if large == sweep else 1)
    cx1, cy1 = coef * rx * y1 / ry, -coef * ry * x1 / rx
    cx = cos * cx1 - sin * cy1 + (p0[0] + p1[0]) / 2
    cy = sin * cx1 + cos * cy1 + (p0[1] + p1[1]) / 2

    def angle(u, v):
        a = math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])
        return a

    theta = angle((1, 0), ((x1 - cx1) / rx, (y1 - cy1) / ry))
    delta = angle(((x1 - cx1) / rx, (y1 - cy1) / ry), ((-x1 - cx1) / rx, (-y1 - cy1) / ry))
    if not sweep and delta > 0:
        delta -= 2 * math.pi
    elif sweep and delta < 0:
        delta += 2 * math.pi
    out = []
    for i in range(n + 1):
        a = theta + delta * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cos * x - sin * y + cx, sin * x + cos * y + cy))
    return out


def path_points(d: str) -> list[tuple[float, float]]:
    tokens = TOKEN.findall(d)
    pts: list[tuple[float, float]] = []
    x = y = sx = sy = 0.0
    last_ctrl = None
    cmd = None
    i = 0
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                x, y = sx, sy
                pts.append((x, y))
                continue
        upper = cmd.upper()
        rel = cmd.islower()
        args = [float(t) for t in tokens[i:i + ARGS[upper]]]
        i += ARGS[upper]
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if upper == "M":
            x, y = args[0] + ox, args[1] + oy
            sx, sy = x, y
            pts.append((x, y))
            cmd = "l" if rel else "L"
            last_ctrl = None
        elif upper in ("L", "T"):
            nx, ny = args[0] + ox, args[1] + oy
            pts += [(x, y), (nx, ny)]
            x, y = nx, ny
            last_ctrl = None
        elif upper == "H":
            x = args[0] + (x if rel else 0)
            pts.append((x, y))
        elif upper == "V":
            y = args[0] + (y if rel else 0)
            pts.append((x, y))
        elif upper == "C":
            c1 = (args[0] + ox, args[1] + oy)
            c2 = (args[2] + ox, args[3] + oy)
            end = (args[4] + ox, args[5] + oy)
            pts += _bezier([(x, y), c1, c2, end])
            last_ctrl, (x, y) = c2, end
        elif upper == "S":
            c1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
            c2 = (args[0] + ox, args[1] + oy)
            end = (args[2] + ox, args[3] + oy)
            pts += _bezier([(x, y), c1, c2, end])
            last_ctrl, (x, y) = c2, end
        elif upper == "Q":
            c = (args[0] + ox, args[1] + oy)
            end = (args[2] + ox, args[3] + oy)
            pts += _bezier([(x, y), c, end])
            last_ctrl, (x, y) = c, end
        elif upper == "A":
            end = (args[5] + ox, args[6] + oy)
            pts += _arc((x, y), args[0], args[1], args[2], int(args[3]), int(args[4]), end)
            x, y = end
            last_ctrl = None
    return pts


def _rotate(points, transform: str | None):
    if not transform:
        return points
    m = re.fullmatch(r"rotate\(([-\d.]+) ([-\d.]+) ([-\d.]+)\)", transform.strip())
    assert m, f"only rotate(a cx cy) transforms are used, not {transform}"
    a, cx, cy = math.radians(float(m.group(1))), float(m.group(2)), float(m.group(3))
    return [(cx + (px - cx) * math.cos(a) - (py - cy) * math.sin(a),
             cy + (px - cx) * math.sin(a) + (py - cy) * math.cos(a)) for px, py in points]


def element_points(el) -> list[tuple[float, float]]:
    tag = el.tag.replace(SVG, "")
    f = {k: float(v) for k, v in el.attrib.items() if k in ("cx", "cy", "r", "rx", "ry", "x", "y", "width", "height")}
    if tag == "path":
        pts = path_points(el.get("d"))
    elif tag == "circle":
        pts = [(f["cx"] + f["r"] * math.cos(t / 16 * math.pi), f["cy"] + f["r"] * math.sin(t / 16 * math.pi))
               for t in range(32)]
    elif tag == "ellipse":
        pts = [(f["cx"] + f["rx"] * math.cos(t / 16 * math.pi), f["cy"] + f["ry"] * math.sin(t / 16 * math.pi))
               for t in range(32)]
    elif tag == "rect":
        x, y, w, h = f["x"], f["y"], f["width"], f["height"]
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    else:
        return []
    return _rotate(pts, el.get("transform"))


def drawing_elements(symbol):
    for el in symbol.iter():
        if el is not symbol and el.tag != f"{SVG}g":
            yield el


# --- the gate ----------------------------------------------------------------------------------------------------

def test_icon_gate():
    builder = load_builder()
    catalogue = {icon: (frame, names) for icon, frame, names in builder.catalogue()}
    root = ET.parse(SOURCE_SPRITE).getroot()
    problems = []
    seen = []
    for symbol in root.iter(f"{SVG}symbol"):
        icon = symbol.get("id")
        seen.append(icon)
        if symbol.get("viewBox") != "0 0 32 32":
            problems.append(f"{icon}: viewBox is not 0 0 32 32")
        if icon not in catalogue:
            problems.append(f"{icon}: no node or facet uses it")
            continue
        facet = icon.startswith("facet.")
        worst = 0.0
        for el in drawing_elements(symbol):
            tag = el.tag.replace(SVG, "")
            if tag not in ("path", "circle", "ellipse", "rect"):
                problems.append(f"{icon}: <{tag}> is not a drawing element")
            extra = set(el.attrib) - ALLOWED_ATTRIBUTES
            if extra:
                problems.append(f"{icon}: attributes {sorted(extra)} (one stroke weight, no styles)")
            for colour in (el.get("fill"), el.get("stroke")):
                if colour not in (None, "none", "currentColor"):
                    problems.append(f"{icon}: colour {colour}; icons take their colour from the page")
            for px, py in element_points(el):
                if facet:
                    lo, hi = FACET_BOX
                    worst = max(worst, lo - px, lo - py, px - hi, py - hi)
                else:
                    worst = max(worst, math.hypot(px - 16, py - 16) - PLACE_RADIUS)
        for g in symbol.iter(f"{SVG}g"):
            for colour in (g.get("fill"), g.get("stroke")):
                if colour not in (None, "none", "currentColor"):
                    problems.append(f"{icon}: group colour {colour}")
        if worst > 1e-6:
            problems.append(f"{icon}: the drawing leaves the frame's clear area by {worst:.2f} units")
    assert len(seen) == len(set(seen)) == 186
    assert set(seen) == set(catalogue)
    assert problems == []


def test_built_sprite_carries_frames_and_titles_and_matches_the_source():
    builder = load_builder()
    assert BUILT_SPRITE.read_text(encoding="utf-8") == builder.sprite_text(), "run scripts/build_icons.py"
    sheet = ROOT / "docs" / "collections" / "svg" / "icons.svg"
    assert sheet.read_text(encoding="utf-8") == builder.sheet_text(), "run scripts/build_icons.py"
    built = ET.parse(BUILT_SPRITE).getroot()
    catalogue = {icon: (frame, names) for icon, frame, names in builder.catalogue()}
    for symbol in built.iter(f"{SVG}symbol"):
        icon = symbol.get("id")
        titles = {t.get("lang"): t.text for t in symbol.findall(f"{SVG}title")}
        assert titles == {"en": catalogue[icon][1]["en"], "es": catalogue[icon][1]["es"]}, icon
        assert symbol.get("stroke-width") == "1.75" and symbol.get("stroke-linejoin") == "round", icon
        first = next(el for el in symbol if el.tag != f"{SVG}title")
        if icon.startswith("facet."):
            assert first.tag == f"{SVG}rect", icon
        else:
            assert first.tag == f"{SVG}circle" and first.get("r") == "13.125", icon
