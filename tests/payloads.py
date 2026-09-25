"""Valid slide-case payloads that tests mutate one rule at a time."""

from __future__ import annotations

import copy

SHA = "a" * 64


def contribution() -> dict:
    """A valid contribution: an ISO slide, a louse on a pocket gopher, one macro photo and one micro scan."""
    return copy.deepcopy({
        "origin": "contribution",
        "slide": {
            "format": "iso_76x26",
            "coverslip": "22x40",
            "preparation": "whole_mount",
            "stain": "unstained",
            "mountant": "Canada balsam",
            "catalogue_number": "LAM-0001",
            "prepared_on": "2019-05",
            "preparer": "A. Preparator",
        },
        "specimen": {
            "anchor": {"kind": "taxon", "ref": "1032608", "name": "Polyplax borealis", "rank": "species"},
            "collected_on": "2019-04-20",
            "collector": "A. Collector",
            "locality_text": "Near a stream",
            "coordinates": {"lat": -33.4489, "lon": -70.6693, "uncertainty_m": 30},
            "geoprivacy": "open",
            "host": {"kind": "taxon", "ref": "2437295", "name": "Thomomys", "rank": "genus"},
        },
        "placement": {"node": "life.insects.lice"},
        "assets": [
            {
                "family": "macro", "role": "slide_overview", "upload_id": "upload-0001",
                "licence": "https://creativecommons.org/licenses/by/4.0/", "creator": "A. Contributor",
                "exif": {"datetime_original": "2019-04-20T10:00:00", "gps_present": True},
            },
            {
                "family": "micro", "role": "single", "upload_id": "upload-0002",
                "licence": "http://creativecommons.org/licenses/by-nc/4.0", "creator": "A. Contributor",
                "pixel_size_um": 0.46, "modality": "brightfield",
            },
        ],
    })


def base() -> dict:
    """A valid base-collection case: every asset carries its source."""
    payload = contribution()
    payload["origin"] = "base"
    for i, asset in enumerate(payload["assets"]):
        asset.pop("upload_id", None)
        asset["licence"] = "https://creativecommons.org/licenses/by/4.0/"
        asset["rights_holder"] = "The Trustees of the Natural History Museum, London"
        asset["source"] = {
            "url": f"https://data.nhm.ac.uk/media/asset-{i}",
            "record_id": f"NHMUK010697793-{i}",
            "retrieved_on": "2026-09-23",
            "sha256": SHA,
        }
    return payload
