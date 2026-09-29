"""The Natural History Museum, London: specimen records with images, from its Data Portal (CKAN datastore).

Records of the Specimens resource carry Darwin Core fields and ``associatedMedia``, each image with its own licence
(CC BY 4.0), rights holder and pixel size, served by a IIIF Image API 3 service at ``identifier``. For a slide from
the digitisation programme, the image titled ``<barcode>_<n>_<n>`` is the whole slide photographed with its labels
(the macro) and the images titled ``<barcode>__<date>-...`` are the microscope images (dossier 10). The anchor is
the GBIF backbone key of the record's GBIF occurrence (``gbifID``), read at curation.
"""

from __future__ import annotations

import json
import re
from datetime import date

from app.base.http import Polite
from app.contracts import licences

API = "https://data.nhm.ac.uk/api/3/action/datastore_search"
SPECIMENS = "05ff2255-c38a-40c9-b657-4ccb55ab2feb"
RECORD = "https://data.nhm.ac.uk/object/"
OCCURRENCE = "https://api.gbif.org/v1/occurrence/"
MACRO_TITLE = re.compile(r"^\d+_\d+_\d+$")


def image_role(title: str) -> str:
    """``macro`` for the photograph of the whole slide, ``micro`` for a microscope image, ``other`` otherwise."""
    if MACRO_TITLE.match(title or ""):
        return "macro"
    if "__" in (title or "") and ("Image Export" in title or "Scene" in title or "ScanRegion" in title):
        return "micro"
    return "other"


def candidate(record: dict) -> dict | None:
    media = []
    for m in record.get("associatedMedia") or []:
        licence = licences.canonical(m.get("license") or "")
        if not licence or not licences.allowed(licence, "base"):
            return None
        service = m["identifier"]
        media.append({
            "media_id": m.get("assetID"),
            "url": f"{service}/full/max/0/default.jpg",
            "iiif": f"{service}/info.json",
            "thumb": f"{service}/full/320,/0/default.jpg",
            "width": int(m.get("PixelXDimension") or 0),
            "height": int(m.get("PixelYDimension") or 0),
            "mime": "image/jpeg",
            "licence": licence,
            "creator": None,
            "rights_holder": m.get("rightsHolder"),
            "title": m.get("title"),
            "role_hint": image_role(m.get("title")),
        })
    if not media:
        return None
    return {
        "source": "nhm",
        "record_id": record.get("catalogNumber"),
        "record_url": RECORD + str(record.get("occurrenceID")),
        "title": record.get("scientificName") or "",
        "description": "; ".join(str(record.get(k)) for k in ("higherClassification", "country", "year", "typeStatus")
                                 if record.get(k)),
        "media": media,
        "hints": {k: record.get(k) for k in ("gbifID", "scientificName", "higherClassification", "typeStatus",
                                             "country", "locality", "year", "preservative", "subDepartment",
                                             "collectionCode", "recordedBy", "occurrenceID", "decimalLatitude",
                                             "decimalLongitude") if record.get(k) not in (None, "")},
        "harvested_on": date.today().isoformat(),
    }


def harvest(http: Polite, query: str, filters: dict | None = None, limit: int = 200, need_micro: bool = True,
            max_read: int = 1500) -> tuple[list[dict], dict]:
    """Imaged specimen records matching a full-text query, as candidates; with ``need_micro``, only records that
    have a microscope image besides the photograph of the slide (read up to ``max_read`` records to find them)."""
    wanted = {"_has_image": True, **(filters or {})}
    out, offset, total, seen = [], 0, None, 0
    while len(out) < limit and seen < max_read:
        data = http.json(API, {"resource_id": SPECIMENS, "q": query, "filters": json.dumps(wanted),
                               "limit": 100, "offset": offset})
        result = data["result"]
        total = result.get("total")
        records = result.get("records", [])
        if not records:
            break
        for record in records:
            seen += 1
            found = candidate(record)
            if found and (not need_micro or any(m["role_hint"] == "micro" for m in found["media"])):
                out.append(found)
        offset += len(records)
    return out[:limit], {"matched": total, "read": seen, "kept": min(len(out), limit)}


def occurrence_taxon(http: Polite, gbif_id: str | int) -> dict:
    """The GBIF backbone taxon of an NHM record, from its GBIF occurrence."""
    o = http.json(f"{OCCURRENCE}{gbif_id}")
    return {k: o.get(k) for k in ("taxonKey", "acceptedTaxonKey", "scientificName", "acceptedScientificName",
                                  "taxonRank", "eventDate", "country", "decimalLatitude", "decimalLongitude",
                                  "recordedBy", "typeStatus")}
