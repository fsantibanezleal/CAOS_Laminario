"""Contact sheets of candidates, so every base-collection slide is chosen by looking at it.

A sheet is a grid of thumbnails, each numbered, with an index file that maps the numbers to records. Dossier 06
requires a person's review: a record can say "slide" and show an accession-register page, and a category can hold
drawings or electron micrographs.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.base.http import Polite, SourceError
from app.imaging.library import vips

CELL = 240
LABEL = 28


def _thumb(http: Polite, url: str | None):
    pv = vips()
    if not url:
        return pv.Image.black(CELL - 12, CELL - 12, bands=3) + 200
    try:
        data = http.get(url).content
    except SourceError:
        return pv.Image.black(CELL - 12, CELL - 12, bands=3) + 120
    image = pv.Image.thumbnail_buffer(data, CELL - 12, height=CELL - 12)
    if image.hasalpha():
        image = image.flatten(background=[255, 255, 255])
    if image.bands == 1:
        image = image.bandjoin([image, image])
    return image.extract_band(0, n=3)


def sheet(candidates: list[dict], out: Path, columns: int = 6, title: str = "") -> Path:
    """Write ``out`` (PNG) and ``out`` with ``.tsv``: thumbnails numbered from 1, in candidate order."""
    pv = vips()
    cells = []
    with Polite(pause_s=0.2) as http:
        for n, c in enumerate(candidates, 1):
            media = c["media"][0] if c["media"] else {}
            image = _thumb(http, media.get("thumb"))
            canvas = (pv.Image.black(CELL, CELL + LABEL, bands=3) + 250).cast("uchar")
            canvas = canvas.insert(image, (CELL - image.width) // 2, (CELL - image.height) // 2)
            text = pv.Image.text(f"{n}  {c['source']}", dpi=110, font="sans 9")
            ink = (text > 0).ifthenelse([20, 20, 20], [250, 250, 250]).cast("uchar")
            canvas = canvas.insert(ink.crop(0, 0, min(ink.width, CELL - 8), ink.height), 6, CELL + 4)
            cells.append(canvas)
    grid = pv.Image.arrayjoin(cells, across=columns, shim=4, background=[180, 180, 180])
    out.parent.mkdir(parents=True, exist_ok=True)
    grid.write_to_file(str(out))
    rows = ["n\tsource\trecord\ttitle\tlicence\tsize\thints"]
    for n, c in enumerate(candidates, 1):
        m = c["media"][0] if c["media"] else {}
        hints = c.get("hints", {})
        hint = "; ".join(hints.get("categories", [])[:4]) if "categories" in hints else json.dumps(
            {k: hints[k] for k in list(hints)[:5]}, ensure_ascii=False)
        rows.append("\t".join([str(n), c["source"], str(c["record_id"]), c["title"][:90], str(m.get("licence")),
                               f"{m.get('width')}x{m.get('height')}", hint[:200]]))
    out.with_suffix(".tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return out
