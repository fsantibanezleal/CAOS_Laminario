"""Geoprivacy in the catalog record: obscured and private coordinates never leave the database."""

from __future__ import annotations

import json

from app.config import Settings
from app.contracts.ingest import SlideCaseSubmission
from app.services import catalog
from app.services.slides import slide_from_submission
from tests import payloads

SETTINGS = Settings(public_base_url="https://laminario.example.org", data_root="unused")
TRUE_LAT, TRUE_LON = -33.4489, -70.6693


def build(geoprivacy: str, short_id: str = "7K3QX9M2"):
    payload = payloads.contribution()
    payload["specimen"]["geoprivacy"] = geoprivacy
    sub = SlideCaseSubmission.model_validate(payload)
    slide = slide_from_submission(sub, new_id=short_id)
    for i, asset in enumerate(slide.assets):
        asset.id = i + 1
    from app.db.base import utcnow
    slide.created_at = slide.updated_at = utcnow()
    return catalog.slide_record(slide, SETTINGS)


def test_obscured_and_private_coordinates_never_leave():
    open_record = build("open")
    assert open_record.place.point.lat == TRUE_LAT and open_record.place.point.lon == TRUE_LON
    assert open_record.place.cell is None

    obscured = build("obscured")
    assert obscured.place.point != open_record.place.point
    cell = obscured.place.cell
    assert cell.south <= TRUE_LAT < cell.north and cell.west <= TRUE_LON < cell.east
    assert abs(cell.north - cell.south - 0.2) < 1e-9 and abs(cell.east - cell.west - 0.2) < 1e-9
    assert cell.south <= obscured.place.point.lat < cell.north
    assert cell.west <= obscured.place.point.lon < cell.east
    assert obscured.place.uncertainty_m is None
    # stable across requests, and the true coordinates appear nowhere in the serialised record
    assert build("obscured").place.point == obscured.place.point
    text = json.dumps(obscured.model_dump(mode="json"))
    assert str(TRUE_LAT) not in text and str(TRUE_LON) not in text

    private = build("private")
    assert private.place.point is None and private.place.cell is None
    text = json.dumps(private.model_dump(mode="json"))
    assert str(TRUE_LAT) not in text and str(TRUE_LON) not in text


def test_obscured_point_depends_on_the_cell_not_the_true_position():
    a = catalog.obscure("7K3QX9M2", -33.41, -70.61)
    b = catalog.obscure("7K3QX9M2", -33.59, -70.79)
    assert a == b
    c = catalog.obscure("AAAAAAAA", -33.41, -70.61)
    assert c[1] == a[1] and c[0] != a[0]


def test_record_carries_permalink_qr_payload_and_media_addresses():
    record = build("open")
    assert record.permalink == "https://laminario.example.org/s/7K3QX9M2"
    assert record.qr_payload == "HTTPS://LAMINARIO.EXAMPLE.ORG/S/7K3QX9M2"
    assert record.assets[1].media.kind == "pyramid"
    assert record.assets[0].media.kind == "image"
    assert record.assets[1].licence.short_name == "CC BY-NC 4.0"
    assert record.quality.badge == "needs_id"
    assert all(check.passed for check in record.quality.checks)
    assert record.manifest_url.endswith("/api/slides/7K3QX9M2/manifest")
