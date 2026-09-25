"""The ingestion contract: every rejecting rule names its field and expected range; flags are reported.

Each case starts from a valid payload and breaks exactly one rule, so a failure names the rule that did not
fire. The rejecting rules are the rows of the design's section 2.1 that this unit enforces (rules needing a
registry or a file belong to U2, U5 and U7).
"""

from __future__ import annotations

import copy
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.contracts.ingest import validate_submission
from app.main import create_app
from tests import payloads

FUTURE = (date.today() + timedelta(days=3)).isoformat()


def set_path(payload: dict, path: str, value) -> dict:
    """Return a copy of ``payload`` with the dotted ``path`` set (an integer segment indexes a list)."""
    out = copy.deepcopy(payload)
    parts = path.split(".")
    cur = out
    for part in parts[:-1]:
        cur = cur[int(part)] if part.isdigit() else cur[part]
    last = parts[-1]
    if last.isdigit():
        cur[int(last)] = value
    else:
        cur[last] = value
    return out


def drop_path(payload: dict, path: str) -> dict:
    out = copy.deepcopy(payload)
    parts = path.split(".")
    cur = out
    for part in parts[:-1]:
        cur = cur[int(part)] if part.isdigit() else cur[part]
    del cur[parts[-1]]
    return out


# (rule, mutated payload, the field the error must name, a fragment the expected text must contain)
REJECTING_CASES = [
    ("format vocabulary", set_path(payloads.contribution(), "slide.format", "glass"), "slide.format", "iso_76x26"),
    (
        "custom format needs a size",
        set_path(payloads.contribution(), "slide.format", "custom"),
        "slide.custom_mm",
        "20 to 100 mm",
    ),
    (
        "custom size range",
        set_path(
            set_path(payloads.contribution(), "slide.format", "custom"), "slide.custom_mm", {"w_mm": 150, "h_mm": 30}
        ),
        "slide.custom_mm.w_mm",
        "20 to 100",
    ),
    (
        "size on a standard format",
        set_path(payloads.contribution(), "slide.custom_mm", {"w_mm": 50, "h_mm": 30}),
        "slide.custom_mm",
        "no size unless",
    ),
    ("coverslip vocabulary", set_path(payloads.contribution(), "slide.coverslip", "30x30"), "slide.coverslip", "18x18"),
    (
        "custom coverslip needs a size",
        set_path(payloads.contribution(), "slide.coverslip", "custom"),
        "slide.coverslip_custom_mm",
        "width and height",
    ),
    (
        "coverslip must fit",
        set_path(
            set_path(payloads.contribution(), "slide.coverslip", "custom"),
            "slide.coverslip_custom_mm",
            {"w_mm": 80, "h_mm": 20},
        ),
        "slide.coverslip_custom_mm",
        "within 76 x 26",
    ),
    (
        "standard coverslip larger than a small slide",
        set_path(
            set_path(
                set_path(payloads.contribution(), "slide.format", "custom"), "slide.custom_mm", {"w_mm": 40, "h_mm": 20}
            ),
            "slide.coverslip",
            "24x60",
        ),
        "slide.coverslip",
        "within 40 x 20",
    ),
    (
        "preparation vocabulary",
        set_path(payloads.contribution(), "slide.preparation", "sliced"),
        "slide.preparation",
        "whole_mount",
    ),
    ("stain length", set_path(payloads.contribution(), "slide.stain", "x" * 81), "slide.stain", "80"),
    (
        "catalogue number length",
        set_path(payloads.contribution(), "slide.catalogue_number", "x" * 65),
        "slide.catalogue_number",
        "64",
    ),
    ("date form", set_path(payloads.contribution(), "slide.prepared_on", "May 2019"), "slide.prepared_on", "YYYY"),
    (
        "date before 1600",
        set_path(payloads.contribution(), "specimen.collected_on", "1599-12-31"),
        "specimen.collected_on",
        "1600",
    ),
    (
        "date in the future",
        set_path(payloads.contribution(), "specimen.collected_on", FUTURE),
        "specimen.collected_on",
        "today",
    ),
    (
        "impossible calendar date",
        set_path(payloads.contribution(), "specimen.collected_on", "2019-02-30"),
        "specimen.collected_on",
        "YYYY",
    ),
    (
        "anchor kind",
        set_path(payloads.contribution(), "specimen.anchor.kind", "fossil"),
        "specimen.anchor.kind",
        "taxon",
    ),
    (
        "taxon ref is a GBIF key",
        set_path(payloads.contribution(), "specimen.anchor.ref", "Polyplax"),
        "specimen.anchor.ref",
        "GBIF",
    ),
    (
        "anchor name required",
        drop_path(payloads.contribution(), "specimen.anchor.name"),
        "specimen.anchor.name",
        "1 to 200",
    ),
    (
        "latitude range",
        set_path(payloads.contribution(), "specimen.coordinates.lat", 95),
        "specimen.coordinates.lat",
        "-90",
    ),
    (
        "longitude range",
        set_path(payloads.contribution(), "specimen.coordinates.lon", -190),
        "specimen.coordinates.lon",
        "-180",
    ),
    (
        "uncertainty not negative",
        set_path(payloads.contribution(), "specimen.coordinates.uncertainty_m", -1),
        "specimen.coordinates.uncertainty_m",
        "at least 0",
    ),
    (
        "geoprivacy vocabulary",
        set_path(payloads.contribution(), "specimen.geoprivacy", "hidden"),
        "specimen.geoprivacy",
        "obscured",
    ),
    ("host is a taxon", set_path(payloads.contribution(), "specimen.host.kind", "rock"), "specimen.host.kind", "taxon"),
    (
        "host ref is a GBIF key",
        set_path(payloads.contribution(), "specimen.host.ref", "Thomomys"),
        "specimen.host.ref",
        "GBIF",
    ),
    (
        "placement node form",
        set_path(payloads.contribution(), "placement.node", "Life/Insects"),
        "placement.node",
        "lowercase",
    ),
    ("at least one asset", set_path(payloads.contribution(), "assets", []), "assets", "1 to 500"),
    (
        "role belongs to family",
        set_path(payloads.contribution(), "assets.0.role", "pyramid"),
        "assets.0.role",
        "slide_overview",
    ),
    (
        "exactly one content",
        set_path(payloads.contribution(), "assets.0.remote_iiif", "https://x.org/iiif/a"),
        "assets.0.upload_id",
        "exactly one",
    ),
    (
        "no content at all",
        drop_path(payloads.contribution(), "assets.1.upload_id"),
        "assets.1.upload_id",
        "exactly one",
    ),
    (
        "licence in the policy",
        set_path(payloads.contribution(), "assets.1.licence", "https://creativecommons.org/licenses/by-nd/4.0/"),
        "assets.1.licence",
        "CC BY-NC 4.0",
    ),
    (
        "nc licence refused for the base collection",
        set_path(payloads.base(), "assets.1.licence", "https://creativecommons.org/licenses/by-nc/4.0/"),
        "assets.1.licence",
        "CC BY-SA",
    ),
    (
        "unknown licence",
        set_path(payloads.contribution(), "assets.1.licence", "all rights reserved"),
        "assets.1.licence",
        "CC0",
    ),
    (
        "rights holder or creator",
        drop_path(payloads.contribution(), "assets.0.creator"),
        "assets.0.rights_holder",
        "rights holder or a creator",
    ),
    (
        "pixel size range",
        set_path(payloads.contribution(), "assets.1.pixel_size_um", 0.01),
        "assets.1.pixel_size_um",
        "0.05 to 50",
    ),
    (
        "micro asset needs a modality",
        drop_path(payloads.contribution(), "assets.1.modality"),
        "assets.1.modality",
        "brightfield",
    ),
    (
        "modality vocabulary",
        set_path(payloads.contribution(), "assets.1.modality", "xray"),
        "assets.1.modality",
        "brightfield",
    ),
    (
        "z plane needs its plane",
        set_path(payloads.contribution(), "assets.1.role", "z_plane"),
        "assets.1.plane",
        "index, depth_um and stack",
    ),
    (
        "plane only on a z plane",
        set_path(payloads.contribution(), "assets.1.plane", {"index": 0, "depth_um": 0, "stack": "s1"}),
        "assets.1.plane",
        "no plane",
    ),
    (
        "polarised needs polarisation",
        set_path(payloads.contribution(), "assets.1.role", "polarised"),
        "assets.1.polarisation",
        "ppl or xpl",
    ),
    (
        "polarisation matches modality",
        set_path(
            set_path(payloads.contribution(), "assets.1.role", "polarised"),
            "assets.1.polarisation",
            {"state": "xpl", "angle_deg": 0},
        ),
        "assets.1.modality",
        "polarised_xpl",
    ),
    (
        "polarisation angle range",
        set_path(
            set_path(
                set_path(payloads.contribution(), "assets.1.role", "polarised"), "assets.1.modality", "polarised_ppl"
            ),
            "assets.1.polarisation",
            {"state": "ppl", "angle_deg": 400},
        ),
        "assets.1.polarisation.angle_deg",
        "0 to 360",
    ),
    ("base asset needs a source", drop_path(payloads.base(), "assets.0.source"), "assets.0.source", "sha256"),
    ("source sha256 form", set_path(payloads.base(), "assets.0.source.sha256", "abc"), "assets.0.source.sha256", "64"),
    ("source url form", set_path(payloads.base(), "assets.0.source.url", "not a url"), "assets.0.source.url", "URL"),
    (
        "source retrieval date not in the future",
        set_path(payloads.base(), "assets.0.source.retrieved_on", FUTURE),
        "assets.0.source.retrieved_on",
        "not in the future",
    ),
    (
        "contribution carries no source",
        set_path(payloads.contribution(), "assets.0.source", payloads.base()["assets"][0]["source"]),
        "assets.0.source",
        "upload_id or remote_iiif",
    ),
    (
        "unknown field refused",
        set_path(payloads.contribution(), "slide.colour", "blue"),
        "slide.colour",
        "no such field",
    ),
    (
        "too many planes in a stack",
        set_path(
            payloads.contribution(),
            "assets",
            [payloads.contribution()["assets"][0]]
            + [
                {
                    "family": "micro",
                    "role": "z_plane",
                    "upload_id": f"upload-{i:04d}",
                    "modality": "brightfield",
                    "licence": "https://creativecommons.org/licenses/by/4.0/",
                    "creator": "A",
                    "plane": {"index": i, "depth_um": i, "stack": "big"},
                }
                for i in range(201)
            ],
        ),
        "assets",
        "at most 200 planes",
    ),
]


@pytest.mark.parametrize("rule,payload,field,fragment", REJECTING_CASES, ids=[c[0] for c in REJECTING_CASES])
def test_every_rejecting_rule_names_field_and_range(rule, payload, field, fragment):
    report = validate_submission(payload)
    assert not report.valid, rule
    hit = [e for e in report.errors if e["field"] == field]
    assert hit, (rule, report.errors)
    assert any(fragment in e["expected"] for e in hit), (rule, hit)


def test_valid_payloads_pass_with_no_errors():
    for payload in (payloads.contribution(), payloads.base()):
        report = validate_submission(payload)
        assert report.valid, report.errors


def test_flagging_rules_accept_and_report():
    payload = payloads.contribution()
    payload["specimen"]["geoprivacy"] = "private"
    payload["assets"][0]["exif"]["datetime_original"] = "2019-04-25T10:00:00"
    del payload["assets"][1]["pixel_size_um"]
    report = validate_submission(payload)
    assert report.valid
    codes = {(f["code"], f["field"]) for f in report.flags}
    assert codes == {
        ("gps_stripped", "assets.0.exif.gps_present"),
        ("exif_date_mismatch", "assets.0.exif.datetime_original"),
        ("not_to_scale", "assets.1.pixel_size_um"),
    }


def test_no_flags_when_nothing_to_flag():
    report = validate_submission(payloads.contribution())
    assert report.valid and report.flags == []


def test_validate_endpoint_answers_422_with_errors_and_200_with_flags():
    with TestClient(create_app()) as client:
        bad = client.post("/api/slide-cases/validate", json=set_path(payloads.contribution(), "slide.format", "glass"))
        assert bad.status_code == 422
        assert bad.json()["valid"] is False
        assert bad.json()["errors"][0]["field"] == "slide.format"
        assert "iso_76x26" in bad.json()["errors"][0]["expected"]

        payload = payloads.contribution()
        del payload["assets"][1]["pixel_size_um"]
        good = client.post("/api/slide-cases/validate", json=payload)
        assert good.status_code == 200
        assert good.json()["valid"] is True
        assert [f["code"] for f in good.json()["flags"]] == ["not_to_scale"]
