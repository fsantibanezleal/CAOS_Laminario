"""Helpers for the collection tests: the icon sprite's symbols, facts for real anchors."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SPRITE = ROOT / "frontend" / "src" / "icons" / "sprite.svg"
BUILT_SPRITE = ROOT / "frontend" / "public" / "icons.svg"
SVG = "{http://www.w3.org/2000/svg}"


def sprite_symbols(path: Path = SOURCE_SPRITE) -> set[str]:
    return {s.get("id") for s in ET.parse(path).getroot().iter(f"{SVG}symbol")}
