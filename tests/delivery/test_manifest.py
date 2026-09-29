"""IIIF Presentation 3 manifests against the pinned IIIF validator schema."""

from __future__ import annotations

import copy
from datetime import date

import jsonschema
import pytest
from fastapi.testclient import TestClient

from app.main import create_app

from .support import make_settings, seed_slide

CC_BY = "https://creativecommons.org/licenses/by/4.0/"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"


def pyramid(key: str, **extra) -> dict:
    return {"family": "micro", "media_kind": "pyramid", "storage_key": key, "width_px": 3840, "height_px": 4608,
            "licence_uri": CC_BY, "creator": "A. Contributor", "pixel_size_um": 0.2289, "modality": "brightfield"
            } | extra


def macro_photo(key: str, **extra) -> dict:
    return {"family": "macro", "role": "slide_overview", "media_kind": "image", "storage_key": key,
            "width_px": 4000, "height_px": 1400, "licence_uri": CC0, "creator": "A. Contributor"} | extra


def remote(url: str, version: int, **extra) -> dict:
    return {"family": "micro", "media_kind": "remote_iiif", "remote_info_url": url, "remote_iiif_version": version,
            "width_px": 7369, "height_px": 3377, "licence_uri": CC_BY,
            "rights_holder": "The Trustees of the Natural History Museum, London",
            "source_url": "https://data.nhm.ac.uk/object/example", "source_record_id": "NHMUK010697793",
            "source_retrieved_on": date(2026, 9, 23), "source_sha256": "a" * 64} | extra


@pytest.fixture(scope="module")
def validator(tmp_path_factory):
    from .support import iiif_schema

    schema = iiif_schema(tmp_path_factory.mktemp("iiif-schema"))
    return jsonschema.Draft7Validator(schema, format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER)


def fetch(tmp_path, assets, **kwargs):
    settings = make_settings(tmp_path)
    slide_id = seed_slide(settings, assets, **kwargs)
    with TestClient(create_app(settings)) as client:
        response = client.get(f"/api/slides/{slide_id}/manifest")
    return slide_id, response


def assert_valid(validator, document):
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    assert not errors, [f"{list(e.absolute_path)}: {e.message}" for e in errors[:5]]


# R-022
def test_manifest_validates(validator, tmp_path):
    stack = [pyramid(f"S1/p{k}.tif", stack="z1", plane_index=k, plane_depth_um=2.0 * k - 2.0) for k in range(3)]
    slide_id, response = fetch(tmp_path / "a", [macro_photo("S1/macro.jpg"), *stack])
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/ld+json")
    assert response.headers["access-control-allow-origin"] == "*"
    document = response.json()
    assert_valid(validator, document)
    canvases = document["items"]
    assert len(canvases) == 4
    assert [c["label"]["en"][0].split(", ")[1] for c in canvases[:3]] == [
        "focal plane 0 at -2 um", "focal plane 1 at 0 um", "focal plane 2 at 2 um"]
    assert canvases[0]["rights"] == "http://creativecommons.org/licenses/by/4.0/"
    assert canvases[3]["rights"] == "http://creativecommons.org/publicdomain/zero/1.0/"
    assert "rights" not in document  # two licences: each canvas carries its own
    body = canvases[0]["items"][0]["items"][0]["body"]
    assert body["service"][0] == {"id": "https://laminario.example.org/iiif/S1%2Fp0.tif", "type": "ImageService3",
                                  "profile": "level2"}
    assert canvases[3]["items"][0]["items"][0]["body"]["format"] == "image/jpeg"
    assert document["navPlace"]["features"][0]["geometry"]["type"] == "Point"
    assert document["partOf"][0]["id"].endswith("/api/collections/life.insects.lice/iiif")
    assert document["homepage"][0]["id"] == f"https://laminario.example.org/s/{slide_id}"

    # the validator is not vacuous: the https form of a licence and a canvas without size are both refused
    broken = copy.deepcopy(document)
    broken["items"][0]["rights"] = "https://creativecommons.org/licenses/by/4.0/"
    assert list(validator.iter_errors(broken))
    broken = copy.deepcopy(document)
    del broken["items"][0]["width"]
    assert list(validator.iter_errors(broken))


def test_remote_service_and_obscured_place(validator, tmp_path):
    info = "https://iiif.example.org/iiif/2/NHMUK010697793/info.json"
    _, response = fetch(tmp_path / "b", [remote(info, 2)], geoprivacy="obscured", origin="base")
    document = response.json()
    assert_valid(validator, document)
    service = document["items"][0]["items"][0]["items"][0]["body"]["service"][0]
    assert service == {"@id": "https://iiif.example.org/iiif/2/NHMUK010697793", "@type": "ImageService2",
                       "profile": "http://iiif.io/api/image/2/level2.json"}
    assert document["rights"] == "http://creativecommons.org/licenses/by/4.0/"  # one licence throughout
    statement = document["items"][0]["requiredStatement"]["value"]["en"][0]
    assert statement.startswith("The Trustees of the Natural History Museum, London, CC BY 4.0")
    assert "source: https://data.nhm.ac.uk/object/example" in statement
    geometry = document["navPlace"]["features"][0]["geometry"]
    assert geometry["type"] == "Polygon"
    lons = [p[0] for p in geometry["coordinates"][0]]
    assert max(lons) - min(lons) == pytest.approx(0.2)


def test_private_place_leaves_no_trace(validator, tmp_path):
    _, response = fetch(tmp_path / "c", [pyramid("S3/p.tif")], geoprivacy="private")
    document = response.json()
    assert_valid(validator, document)
    assert "navPlace" not in document
    labels = {entry["label"]["en"][0] for entry in document["metadata"]}
    assert "Locality" not in labels


def test_draft_has_no_manifest(tmp_path):
    _, response = fetch(tmp_path / "d", [pyramid("S4/p.tif")], publish=False)
    assert response.status_code == 404
