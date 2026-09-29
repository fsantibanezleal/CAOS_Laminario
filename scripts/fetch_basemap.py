#!/usr/bin/env python3
"""Fetch the world basemap: a zoom 0 to 7 extract of one Protomaps daily build (dossier 12, section 3).

The map places slides at country level, and an obscured contribution in a 0.2 degree cell, which is 18 px wide at
zoom 7; nothing finer is needed, and MapLibre overzooms the last level. The extract is cut from the pinned build with
go-pmtiles (``pmtiles extract --maxzoom=7``), which reads only the byte ranges it needs (188 MB of a 138 GB planet).
Two extracts of the same build were byte-identical on 2026-09-29, so the result is checked against its SHA-256.

The data is OpenStreetMap's (ODbL 1.0) through the Protomaps basemap schema 4.15.2; the map shows the attribution.
The file goes to ``<LAMINARIO_FIXTURES>/basemap/`` (or ``--out``), outside the repository; ``LAMINARIO_BASEMAP``
names it for the API, and production nginx serves it from the data volume.

    python scripts/fetch_basemap.py [--out FOLDER] [--pmtiles PATH]

The go-pmtiles binary (1.31.2, BSD-3-Clause) is taken from ``--pmtiles``, ``LAMINARIO_PMTILES_BIN`` or the PATH:
https://github.com/protomaps/go-pmtiles/releases/tag/v1.31.2
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

BUILD = "20260928"
SOURCE = f"https://build.protomaps.com/{BUILD}.pmtiles"
MAX_ZOOM = 7
NAME = f"world-z{MAX_ZOOM}-{BUILD}.pmtiles"
BYTES = 188_341_959
SHA256 = "7d21f20a23fe9bbe065c50d1f5c89b8e9fa4984989baf4166d943f7b84d6aef6"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _tool(given: str | None) -> str:
    tool = given or os.environ.get("LAMINARIO_PMTILES_BIN") or shutil.which("pmtiles")
    if not tool:
        raise SystemExit("go-pmtiles 1.31.2 is needed: pass --pmtiles or set LAMINARIO_PMTILES_BIN")
    return tool


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, help="the folder to write into (default <LAMINARIO_FIXTURES>/basemap)")
    parser.add_argument("--pmtiles", help="the go-pmtiles binary")
    args = parser.parse_args()
    folder = args.out or (Path(os.environ["LAMINARIO_FIXTURES"]) / "basemap" if "LAMINARIO_FIXTURES" in os.environ
                          else None)
    if folder is None:
        raise SystemExit("pass --out or set LAMINARIO_FIXTURES")
    target = folder / NAME
    if target.is_file() and target.stat().st_size == BYTES and _sha256(target) == SHA256:
        print(f"{target}: present and verified")
        return 0
    folder.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".partial")
    partial.unlink(missing_ok=True)
    subprocess.run([_tool(args.pmtiles), "extract", SOURCE, str(partial), f"--maxzoom={MAX_ZOOM}",
                    "--download-threads=4"], check=True)
    digest = _sha256(partial)
    if digest != SHA256:
        partial.unlink()
        raise SystemExit(f"the extract's SHA-256 is {digest}, not the recorded {SHA256}: the build changed")
    partial.replace(target)
    print(f"{target}: {BYTES / 1e6:.0f} MB, verified; set LAMINARIO_BASEMAP={target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
