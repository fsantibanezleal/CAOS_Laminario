#!/usr/bin/env python3
"""Build the interface's three faces as self-hosted WOFF2 subsets, with their licences (docs/design/visual-system.md).

The upstream files come from the google/fonts repository at a fixed commit and must match their recorded SHA-256;
they are cached in ``<LAMINARIO_FIXTURES>/fonts`` (never in git). The output goes to ``frontend/public/fonts``:

- ``laminario-sans-roman.woff2`` and ``laminario-sans-italic.woff2``: Source Sans 3 (Paul D. Hunt, Adobe), variable
  weight 200-900. The font has the Reserved Font Name "Source", and a subset is not functionally equivalent to the
  original (OFL FAQ 2.7), so the subset is renamed "Laminario Sans" in its name table.
- ``fraunces-display.woff2``: Fraunces instanced at SOFT 50 and WONK 0, weight limited to 400-700, optical size kept.
- ``courier-prime-{regular,italic,bold}.woff2``: Courier Prime as released.

Each face's ``OFL.txt`` is copied beside it. The subset holds Basic Latin, Latin-1 and the symbols a catalogue
writes, with every OpenType feature kept. ``--check`` rebuilds in memory and fails when a committed file differs.

Usage: ``python scripts/build_fonts.py [--check]``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "fonts"
COMMIT = "23e54b51ddffbc7713c583748e3bd86f62b1fa4a"  # google/fonts main on 2026-09-24
UPSTREAM = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl/"

SOURCES = {
    "sourcesans3/SourceSans3[wght].ttf": "042fe2cc0b933e328410d7acbd0aa6a1873dca5aef81875f4bc214b08825c7b9",
    "sourcesans3/SourceSans3-Italic[wght].ttf": "39e3ab05ccd7cb94907c31005bb5bec1d5432f0b096a2b782976e217a540eb6c",
    "sourcesans3/OFL.txt": "09746787287a289323b0ec3cff4d1a4a801331b82b7207c1e186f5d26619a392",
    "fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf": "177ff6c0f14e5550a3c624247cd1189611d4eb65d000b14944c63d967958abbb",
    "fraunces/OFL.txt": "bdf4c22802eaf804f998195871c6b8938aac2ac14b2d78a8bd66a6f1eced833b",
    "courierprime/CourierPrime-Regular.ttf": "72f793376f8e2841656bf21d77a5de010f2929bd6956a22ee848ad0c7eb978af",
    "courierprime/CourierPrime-Italic.ttf": "f1b9a5829789f7e56432a9f3bc7665ef4531dbba1c112639e48bef39621a006b",
    "courierprime/CourierPrime-Bold.ttf": "ff1f38786c849d1c41fa8e447960abdb2bd75fdfb0cfcdeb524fad65a5af3638",
    "courierprime/OFL.txt": "9a755af092b494944c99f471be6fddd19b006a448fefdc4717e4ee0aa09a97b0",
}

#: Basic Latin, Latin-1 (Spanish), and the typographic and scientific symbols the interface and the labels write. The
#: em-dash is written as its escape: the content guard bans the character in the sources, but a source text a slide
#: quotes may hold one, and the face must draw it.
EXTRA = "–—‘’“”…′″♀♂≈≤≥‰•·→№"
TEXT = "".join(chr(c) for c in range(0x20, 0x7F)) + "".join(chr(c) for c in range(0xA0, 0x100)) + EXTRA

RENAMED = "Laminario Sans"


def cache() -> Path:
    root = os.environ.get("LAMINARIO_FIXTURES")
    if not root:
        from app.config import Settings

        root = str(Settings().fixtures or "")
    if not root:
        raise SystemExit("LAMINARIO_FIXTURES names the data vault where upstream fonts are cached")
    folder = Path(root) / "fonts"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def upstream(path: str) -> bytes:
    """The upstream file, from the cache or the pinned commit, checked against its SHA-256."""
    local = cache() / path.replace("/", "__")
    if not local.exists():
        url = UPSTREAM + path.replace("[", "%5B").replace("]", "%5D")
        request = urllib.request.Request(url, headers={"User-Agent": "Laminario font build"})
        with urllib.request.urlopen(request, timeout=120) as response:
            local.write_bytes(response.read())
    data = local.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SOURCES[path]:
        raise SystemExit(f"{path}: SHA-256 {digest} is not the recorded {SOURCES[path]}")
    return data


def woff2(font: TTFont) -> bytes:
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=TEXT)
    subsetter.subset(font)
    font.recalcTimestamp = False  # the build is reproducible: --check compares bytes
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out, reorderTables=False)
    return out.getvalue()


def rename(font: TTFont, style: str) -> None:
    """Replace the Reserved Font Name in every name record: family, full, PostScript and typographic names."""
    table = font["name"]
    postscript = RENAMED.replace(" ", "") + "-" + style.replace(" ", "")
    for record in table.names:
        value = record.toUnicode()
        if record.nameID in (1, 16, 21):
            new = RENAMED
        elif record.nameID in (4,):
            new = f"{RENAMED} {style}"
        elif record.nameID in (6, 20):
            new = postscript
        elif record.nameID == 3:
            new = f"{postscript};built-from-{COMMIT[:12]}"
        elif record.nameID == 25:
            new = RENAMED.replace(" ", "")
        else:
            new = value.replace("Source Sans 3", RENAMED).replace("SourceSans3", RENAMED.replace(" ", ""))
        record.string = new
    table.setName(f"{RENAMED} is a subset of Source Sans 3 by Paul D. Hunt (Adobe), renamed as the SIL Open Font "
                  "License requires of a Modified Version of a font with a Reserved Font Name.", 10, 3, 1, 0x409)


def build() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for src, style, name in (("sourcesans3/SourceSans3[wght].ttf", "Regular", "laminario-sans-roman.woff2"),
                             ("sourcesans3/SourceSans3-Italic[wght].ttf", "Italic", "laminario-sans-italic.woff2")):
        font = TTFont(io.BytesIO(upstream(src)))
        rename(font, style)
        files[name] = woff2(font)
    fraunces = TTFont(io.BytesIO(upstream("fraunces/Fraunces[SOFT,WONK,opsz,wght].ttf")))
    fraunces = instancer.instantiateVariableFont(fraunces, {"SOFT": 50, "WONK": 0, "wght": (400, 700)})
    files["fraunces-display.woff2"] = woff2(fraunces)
    for style in ("Regular", "Italic", "Bold"):
        font = TTFont(io.BytesIO(upstream(f"courierprime/CourierPrime-{style}.ttf")))
        files[f"courier-prime-{style.lower()}.woff2"] = woff2(font)
    # The licence texts are stored with LF line endings, as git keeps text in this repository (upstream has CRLF).
    for name, src in (("laminario-sans", "sourcesans3"), ("fraunces", "fraunces"), ("courier-prime", "courierprime")):
        files[f"{name}-OFL.txt"] = upstream(f"{src}/OFL.txt").replace(b"\r\n", b"\n")
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail when a committed file differs from a rebuild")
    args = parser.parse_args()
    files = build()
    if args.check:
        stale = [n for n, data in files.items() if not (OUT / n).exists() or (OUT / n).read_bytes() != data]
        if stale:
            print("fonts differ from a rebuild:", ", ".join(stale))
            return 1
        print(f"fonts: {len(files)} files match a rebuild")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (OUT / name).write_bytes(data)
        print(f"{name}: {len(data) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
