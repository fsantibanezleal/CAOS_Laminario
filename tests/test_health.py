from fastapi.testclient import TestClient

from app.main import create_app
from app.version import VERSION, semver


def test_health_reports_product_and_version():
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "product": "laminario", "version": VERSION}


def test_version_file_is_padded_display_form_and_semver_drops_the_padding():
    major, minor, patch = VERSION.split(".")
    assert (len(major), len(minor), len(patch)) == (1, 2, 3)
    assert semver("0.12.003") == "0.12.3"
    assert semver("1.00.000") == "1.0.0"
