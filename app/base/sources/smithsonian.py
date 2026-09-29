"""The Smithsonian Open Access API: records of the Smithsonian units whose media are released as CC0.

``GET https://api.si.edu/openaccess/api/v1.0/search?q=&rows=&start=&api_key=`` answers rows with a ``content`` block:
``descriptiveNonRepeating`` holds the record id (``record_ID``), the unit and ``online_media.media``, each with its
IDS identifier (``idsId``), the delivery URL (``content``, which also serves the full size without ``max=``) and its
usage (``usage.access`` is ``CC0`` for open media); ``freetext.notes`` carries the archive's description. The key is
an api.data.gov key; ``DEMO_KEY`` is enough for a harvest (it allows 30 requests an hour).

The base collection uses it for Wilson A. Bentley's snow-crystal photomicrographs in the Smithsonian Institution
Archives, whose titles name Bentley's own type (stellar, tabular, lamellar, fernlike, granular, columnar).
"""

from __future__ import annotations

import os
from datetime import date

from app.base.http import Polite

API = "https://api.si.edu/openaccess/api/v1.0/search"
DELIVERY = "https://ids.si.edu/ids/deliveryService?id="
RECORD = "https://collections.si.edu/search/detail/edanmdm:"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
UNIT_HOLDERS = {"SIA": "Smithsonian Institution Archives"}


def api_key() -> str:
    return os.environ.get("LAMINARIO_SI_API_KEY") or "DEMO_KEY"


def _notes(content: dict) -> str:
    return " ".join(n.get("content", "") for n in content.get("freetext", {}).get("notes", []))


def _names(content: dict) -> list[str]:
    return [n.get("content", "") for n in content.get("freetext", {}).get("name", [])]


def candidate(row: dict) -> dict | None:
    content = row.get("content", {})
    described = content.get("descriptiveNonRepeating", {})
    media = []
    for m in described.get("online_media", {}).get("media", []):
        if m.get("usage", {}).get("access") != "CC0" or m.get("type") not in (None, "Images"):
            continue
        ids = m.get("idsId")
        if not ids:
            continue
        creator = next((n for n in _names(content) if "Bentley" in n), None) or (_names(content) or [None])[0]
        media.append({"media_id": ids, "url": DELIVERY + ids, "thumb": DELIVERY + ids + "&max=320",
                      "width": None, "height": None, "mime": "image/jpeg", "licence": CC0,
                      "creator": creator[:200] if creator else None,
                      "rights_holder": UNIT_HOLDERS.get(row.get("unitCode"), "Smithsonian Institution"),
                      "credit": described.get("data_source"), "date": None})
    if not media:
        return None
    record_id = described.get("record_ID") or row.get("id")
    return {
        "source": "smithsonian",
        "record_id": record_id,
        "record_url": RECORD + record_id,
        "title": row.get("title", ""),
        "description": _notes(content)[:600],
        "media": media[:1],
        "hints": {"unit": row.get("unitCode"), "categories": []},
        "harvested_on": date.today().isoformat(),
    }


def harvest(http: Polite, query: str, limit: int = 100, title_contains: str | None = None) -> tuple[list[dict], dict]:
    """Records matching a query that hold at least one CC0 image; ``title_contains`` narrows by title."""
    out, start, total = [], 0, None
    counts = {"records": 0, "kept": 0}
    while len(out) < limit:
        data = http.json(API, {"q": query, "rows": min(100, limit), "start": start, "api_key": api_key()})
        rows = data.get("response", {}).get("rows", [])
        total = data.get("response", {}).get("rowCount", 0)
        for row in rows:
            counts["records"] += 1
            if title_contains and title_contains.lower() not in row.get("title", "").lower():
                continue
            found = candidate(row)
            if found:
                out.append(found)
        start += len(rows)
        if not rows or start >= total:
            break
    counts["kept"] = len(out)
    return out[:limit], counts
