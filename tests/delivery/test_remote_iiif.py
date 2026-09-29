"""The remote-asset contract against a local server that answers the way real services do, and fail."""

from __future__ import annotations

import pytest

from app.delivery.remote import check_remote_asset

from .support import json_body, serve

ORIGIN = "https://laminario.example.org"
CORS = {"Access-Control-Allow-Origin": "*", "Content-Type": "application/ld+json"}


def info3(**extra) -> dict:
    return {"@context": "http://iiif.io/api/image/3/context.json", "id": "https://example.org/iiif/x",
            "type": "ImageService3", "protocol": "http://iiif.io/api/image", "profile": "level2",
            "width": 7369, "height": 3377, "rights": "http://creativecommons.org/licenses/by/4.0/"} | extra


def info2(**extra) -> dict:
    return {"@context": "http://iiif.io/api/image/2/context.json", "@id": "https://example.org/iiif/y",
            "protocol": "http://iiif.io/api/image", "profile": ["http://iiif.io/api/image/2/level2.json"],
            "width": 7369, "height": 3377, "license": ["https://creativecommons.org/licenses/by/4.0/"]} | extra


ROUTES = {
    "/good3/info.json": (200, CORS, json_body(info3())),
    "/good2/info.json": (200, CORS, json_body(info2())),
    "/own-origin/info.json": (200, CORS | {"Access-Control-Allow-Origin": ORIGIN}, json_body(info3())),
    "/no-rights/info.json": (200, CORS, json_body({k: v for k, v in info3().items() if k != "rights"})),
    "/nd-rights/info.json": (200, CORS, json_body(info3(rights="http://creativecommons.org/licenses/by-nd/4.0/"))),
    "/nc-rights/info.json": (200, CORS, json_body(info3(rights="http://creativecommons.org/licenses/by-nc/4.0/"))),
    "/no-cors/info.json": (200, {"Content-Type": "application/json"}, json_body(info3())),
    "/other-origin/info.json": (200, CORS | {"Access-Control-Allow-Origin": "https://elsewhere.example"},
                                json_body(info3())),
    "/resized/info.json": (200, CORS, json_body(info3(width=3684, height=1688))),
    "/not-iiif/info.json": (200, CORS, json_body({"width": 7369, "height": 3377})),
    "/not-json/info.json": (200, {"Content-Type": "text/html"}, b"<html>maintenance</html>"),
    "/gone/info.json": (410, {}, b"gone"),
}

EXPECTED = {
    ("good3", "base"): [],
    ("good2", "base"): [],
    ("own-origin", "base"): [],
    ("nc-rights", "contribution"): [],
    ("no-rights", "base"): ["rights"],
    ("nd-rights", "contribution"): ["rights"],
    ("nc-rights", "base"): ["rights"],
    ("no-cors", "base"): ["cors"],
    ("other-origin", "base"): ["cors"],
    ("resized", "base"): ["dimensions"],
    ("not-iiif", "base"): ["protocol", "rights"],
    ("not-json", "base"): ["availability"],
    ("gone", "base"): ["availability"],
    ("missing", "base"): ["availability"],
}


@pytest.fixture(scope="module")
def remote_server():
    with serve(ROUTES) as url:
        yield url


# R-023
@pytest.mark.parametrize("case, origin", sorted(EXPECTED))
def test_remote_asset_contract(remote_server, case, origin):
    result = check_remote_asset(f"{remote_server}/{case}/info.json", width=7369, height=3377, origin=origin,
                                request_origin=ORIGIN)
    assert [p.field for p in result.problems] == EXPECTED[(case, origin)]
    assert result.ok == (not EXPECTED[(case, origin)])
    for problem in result.problems:
        assert problem.message and problem.expected  # every refusal says what was found and what is expected


def test_accepted_services_report_version_and_licence(remote_server):
    three = check_remote_asset(f"{remote_server}/good3/info.json", width=7369, height=3377, origin="base",
                               request_origin=ORIGIN)
    two = check_remote_asset(f"{remote_server}/good2/info.json", width=7369, height=3377, origin="base",
                             request_origin=ORIGIN)
    assert (three.version, two.version) == (3, 2)
    assert three.licence_uri == two.licence_uri == "https://creativecommons.org/licenses/by/4.0/"
    assert (three.width, three.height) == (7369, 3377)


def test_unreachable_host_is_an_availability_problem():
    result = check_remote_asset("http://127.0.0.1:9/info.json", width=1, height=1, origin="base",
                                request_origin=ORIGIN)
    assert [p.field for p in result.problems] == ["availability"]
