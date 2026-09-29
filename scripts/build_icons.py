"""Build the icon sprite the web uses, and the contact sheet the docs show, from the hand-drawn source.

Source: ``frontend/src/icons/sprite.svg``, one ``<symbol>`` per icon with only its drawing. This adds what every
icon of a kind shares, so it is the same by construction:

- the stroke (currentColor, 1.75 units, round caps and joins, no fill unless a mark asks for one);
- the frame: the field-of-view circle for a place (a realm gets the four reticle ticks too), the rounded square
  for a facet value;
- the titles, in English and Spanish, from the collection tree and the facet vocabularies.

Outputs: ``frontend/public/icons.svg`` (the sprite, used as ``<svg><use href="/icons.svg#life.birds"/></svg>``) and
``docs/collections/svg/icons.svg`` (every icon at 48 and 16 pixels with its id, in both themes).

    python scripts/build_icons.py            # write both
    python scripts/build_icons.py --check    # exit 1 when a committed output differs
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.collections.tree import load_tree  # noqa: E402
from app.services.collections import facets  # noqa: E402

SOURCE = ROOT / "frontend" / "src" / "icons" / "sprite.svg"
SPRITE = ROOT / "frontend" / "public" / "icons.svg"
SHEET = ROOT / "docs" / "collections" / "svg" / "icons.svg"
SVG_NS = "http://www.w3.org/2000/svg"
STROKE = 'fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"'
FIELD = '<circle cx="16" cy="16" r="13.125"/>'
RETICLE = FIELD + '<path d="M16 2.875v1.75M16 27.375v1.75M2.875 16h1.75M27.375 16h1.75"/>'
SQUARE = '<rect x="4.875" y="4.875" width="22.25" height="22.25" rx="3"/>'


def source_symbols() -> dict[str, str]:
    """Each symbol's inner markup, as written, by id."""
    ET.register_namespace("", SVG_NS)
    root = ET.parse(SOURCE).getroot()
    out = {}
    for symbol in root.iter(f"{{{SVG_NS}}}symbol"):
        inner = "".join(ET.tostring(child, encoding="unicode") for child in symbol)
        out[symbol.get("id")] = re.sub(r'\s*xmlns="[^"]+"', "", inner).strip()
    return out


def catalogue() -> list[tuple[str, str, dict[str, str]]]:
    """Every icon the product uses, in tree order then facets: (id, frame, names)."""
    out: list[tuple[str, str, dict[str, str]]] = []
    seen: set[str] = set()
    for node in load_tree().walk():
        if node.icon in seen:
            continue
        seen.add(node.icon)
        out.append((node.icon, RETICLE if node.level == "realm" else FIELD, node.name))
    for facet in facets():
        for value in facet.values:
            out.append((value.icon, SQUARE, {"en": value.name.en, "es": value.name.es}))
    return out


def sprite_text() -> str:
    drawings = source_symbols()
    lines = ['<svg xmlns="http://www.w3.org/2000/svg">',
             "<!-- Built by scripts/build_icons.py from frontend/src/icons/sprite.svg; do not edit. -->"]
    for icon, frame, names in catalogue():
        titles = "".join(f'<title lang="{lang}">{escape(names[lang])}</title>' for lang in ("en", "es"))
        lines.append(f'<symbol id="{icon}" viewBox="0 0 32 32" {STROKE}>{titles}{frame}{drawings[icon]}</symbol>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def sheet_text() -> str:
    """Every icon at 48 px with its id, and at 16 px beside it, twelve to a row."""
    drawings = source_symbols()
    icons = catalogue()
    columns, cell_w, cell_h, top = 8, 150, 96, 64
    rows = -(-len(icons) // columns)
    width, height = columns * cell_w + 32, top + rows * cell_h + 24
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-labelledby="t d">',
        '<title id="t">Laminario icons</title>',
        f'<desc id="d">All {len(icons)} icons: the three realms with their reticle, the collections, sub-collections '
        'and groups in the field-of-view circle, and the facet values in the square, each at 48 and 16 pixels.</desc>',
        "<style>:root{--bg:#fbfaf7;--ink:#1d232b;--muted:#5b6573}"
        "@media (prefers-color-scheme: dark){:root{--bg:#0f1419;--ink:#e6e9ee;--muted:#9aa5b4}}"
        ".bg{fill:var(--bg)}.i{color:var(--ink)}"
        '.h{font:700 15px system-ui,-apple-system,"Segoe UI",sans-serif;fill:var(--ink)}'
        '.l{font:10.5px ui-monospace,"Cascadia Mono",Consolas,monospace;fill:var(--muted)}</style>',
        "<defs>",
    ]
    for icon, frame, _ in icons:
        parts.append(f'<symbol id="{icon}" viewBox="0 0 32 32" {STROKE}>{frame}{drawings[icon]}</symbol>')
    parts += ["</defs>", f'<rect class="bg" x="0" y="0" width="{width}" height="{height}"/>',
              f'<text class="h" x="16" y="36">Laminario icons, {len(icons)} (48 px and 16 px)</text>']
    for i, (icon, _, _) in enumerate(icons):
        x, y = 16 + (i % columns) * cell_w, top + (i // columns) * cell_h
        label = icon if len(icon) <= 24 else "..." + icon[-21:]
        parts.append(f'<g class="i"><use href="#{icon}" xlink:href="#{icon}" x="{x + 28}" y="{y}" width="48" '
                     f'height="48"/><use href="#{icon}" xlink:href="#{icon}" x="{x + 84}" y="{y + 16}" width="16" '
                     f'height="16"/></g><text class="l" x="{x + 4}" y="{y + 66}">{escape(label)}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = {SPRITE: sprite_text(), SHEET: sheet_text()}
    stale = [p for p, text in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if args.check:
        for p in stale:
            print(f"{p.relative_to(ROOT)} is stale: run scripts/build_icons.py")
        return 1 if stale else 0
    for p, text in outputs.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
