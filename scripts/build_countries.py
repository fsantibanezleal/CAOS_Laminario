#!/usr/bin/env python3
"""Build the country vocabulary and the country shapes from their sources in the data vault (dossier 12).

- ``app/collections/data/vocab/countries.json``: every ISO 3166-1 alpha-2 code with its English and Spanish name,
  from Unicode CLDR 48.2.2 (``cldr-localenames-full``, ``main/{en,es}/territories.json``; Unicode License v3). CLDR's
  two-letter codes that are not countries (the European Union, the eurozone, Outlying Oceania, the United Nations,
  the unknown region and the pseudo-locales) are left out.
- ``app/collections/data/countries.geojson``: one feature per code, from Natural Earth 1:50m admin-0 map units
  (public domain; the GeoJSON of nvkelso/natural-earth-vector at commit 117488dc, 2022-05-05). Map units rather than
  countries, because they give the French overseas regions (Guadeloupe, Martinique, Reunion, French Guiana,
  Mayotte) and Svalbard their own shapes; ``ISO_A2_EH`` codes France, Norway, Kosovo and Taiwan where ``ISO_A2``
  does not. Units of one code are merged (the four nations of the United Kingdom into GB), coordinates are rounded to
  0.01 degree (about 1 km: the map shades countries up to zoom 7), and units Natural Earth leaves uncoded (-99) are
  dropped. A few codes have no shape at this scale (Gibraltar, Bouvet Island, the US Minor Outlying Islands and the
  codes CLDR carries for Ascension, Clipperton, Diego Garcia, Ceuta and Melilla, the Canary Islands, Sark and Tristan
  da Cunha); they are valid codes, listed but not shaded.
  Each feature keeps Natural Earth's hand-placed label point (``LABEL_X``, ``LABEL_Y``) and the zoom from which it is
  labelled (``MIN_LABEL``); for merged units, the point of the largest unit and the smallest zoom of them all.

The sources are read from ``<LAMINARIO_FIXTURES>/vocab`` and must match their recorded SHA-256. ``--check`` rebuilds
in memory and fails when a committed file differs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOCAB = ROOT / "app" / "collections" / "data" / "vocab" / "countries.json"
SHAPES = ROOT / "app" / "collections" / "data" / "countries.geojson"

SOURCES = {
    "cldr-48.2.2/en-territories.json": "158c1d575308f7e46912edbeda435c8fe2ef5dad280798231f3a432e406b1807",
    "cldr-48.2.2/es-territories.json": "027b9c91d4e923d506b404415648691ef41ebde721aa454cee4d9f7f66b3ea62",
    "natural-earth/ne_50m_admin_0_map_units.geojson":
        "b8d421aca6e9e08e8cdf09cc26af111cc3e0deba4fe915611d58ade71e8a4db0",
}
NOT_COUNTRIES = {"EU", "EZ", "QO", "UN", "ZZ", "XA", "XB"}


def vault() -> Path:
    root = os.environ.get("LAMINARIO_FIXTURES")
    if not root:
        sys.path.insert(0, str(ROOT))
        from app.config import Settings

        root = str(Settings().fixtures or "")
    if not root:
        raise SystemExit("LAMINARIO_FIXTURES names the data vault holding the sources (vocab/)")
    return Path(root) / "vocab"


def source(name: str) -> bytes:
    data = (vault() / name).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SOURCES[name]:
        raise SystemExit(f"{name}: SHA-256 {digest} is not the recorded {SOURCES[name]}")
    return data


def names() -> dict:
    tables = {lang: json.loads(source(f"cldr-48.2.2/{lang}-territories.json"))["main"][lang]["localeDisplayNames"]
              ["territories"] for lang in ("en", "es")}
    codes = sorted(k for k in tables["en"] if len(k) == 2 and k.isalpha() and k not in NOT_COUNTRIES)
    return {
        "about": "ISO 3166-1 alpha-2 codes with their English and Spanish names, from Unicode CLDR 48.2.2 "
                 "(Unicode License v3). Built by scripts/build_countries.py; do not edit by hand.",
        "countries": {code: {"en": tables["en"][code], "es": tables["es"].get(code, tables["en"][code])}
                      for code in codes},
    }


def _round_ring(ring: list) -> list:
    out = []
    for lon, lat in ring:
        point = [round(lon, 2), round(lat, 2)]
        if not out or out[-1] != point:
            out.append(point)
    if out and out[0] != out[-1]:
        out.append(out[0])
    return out


def _polygons(geometry: dict) -> list:
    polys = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    out = []
    for poly in polys:
        rings = [_round_ring(r) for r in poly]
        rings = [r for r in rings if len(r) >= 4]
        if rings:
            out.append(rings)
    return out


def _area(polys: list) -> float:
    """The planar area of the outer rings, in square degrees: enough to tell the largest unit of a code."""
    return sum(abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False))) / 2
               for ring in (poly[0] for poly in polys))


def shapes(valid: set[str]) -> dict:
    features = json.loads(source("natural-earth/ne_50m_admin_0_map_units.geojson"))["features"]
    merged: dict[str, list] = {}
    labels: dict[str, tuple[float, list[float], float]] = {}
    for f in features:
        props = f["properties"]
        code = props.get("ISO_A2_EH")
        if code in valid:
            polys = _polygons(f["geometry"])
            merged.setdefault(code, []).extend(polys)
            area = _area(polys)
            point = [round(props["LABEL_X"], 2), round(props["LABEL_Y"], 2)]
            best = labels.get(code)
            zoom = min(props["MIN_LABEL"], best[2]) if best else props["MIN_LABEL"]
            labels[code] = (area, point, zoom) if not best or area > best[0] else (best[0], best[1], zoom)
    return {
        "type": "FeatureCollection",
        "about": "Country shapes from Natural Earth 1:50m admin-0 map units (public domain), one feature per ISO "
                 "3166-1 code, rounded to 0.01 degree. Built by scripts/build_countries.py; do not edit by hand.",
        "features": [{"type": "Feature", "id": code,
                      "properties": {"code": code, "label": labels[code][1], "label_zoom": labels[code][2]},
                      "geometry": {"type": "MultiPolygon", "coordinates": polys}}
                     for code, polys in sorted(merged.items())],
    }


def build() -> dict[Path, str]:
    vocab = names()
    geo = shapes(set(vocab["countries"]))
    return {VOCAB: json.dumps(vocab, indent=1, ensure_ascii=False) + "\n",
            SHAPES: json.dumps(geo, separators=(",", ":")) + "\n"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = build()
    if args.check:
        stale = [str(p.relative_to(ROOT)) for p, text in files.items()
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            print("differs from a rebuild:", ", ".join(stale))
            return 1
        print("countries: the vocabulary and the shapes match a rebuild")
        return 0
    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"{path.relative_to(ROOT)}: {len(text.encode('utf-8')) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
