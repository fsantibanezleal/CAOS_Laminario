"""Plain images (macro photographs, height maps) are served by their storage key, for published slides only (F-039:
their /media/ addresses had no route until the slide place first drew them)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app

from .support import make_settings, seed_slide

CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
JPEG = b"\xff\xd8\xff\xe0" + b"laminario" * 20 + b"\xff\xd9"
SHOWN, DRAFT = "PHOTOS01/1-aaaaaaaaaaaa.jpg", "PHOTOS01/2-bbbbbbbbbbbb.jpg"


def photo(key: str) -> dict:
    return {"family": "macro", "role": "slide_overview", "media_kind": "image", "storage_key": key,
            "width_px": 400, "height_px": 140, "licence_uri": CC0, "creator": "A. Contributor"}


def test_a_published_image_is_served_and_nothing_else(tmp_path):
    settings = make_settings(tmp_path)
    slide = seed_slide(settings, [photo(SHOWN)])
    seed_slide(settings, [photo(DRAFT)], publish=False)
    for key in (SHOWN, DRAFT):
        path = settings.store_root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(JPEG)
    with TestClient(create_app(settings)) as client:
        url = client.get(f"/api/slides/{slide}").json()["assets"][0]["media"]["image_url"]
        assert url == f"https://laminario.example.org/media/{SHOWN}"
        served = client.get(f"/media/{SHOWN}")
        assert served.status_code == 200 and served.content == JPEG
        assert served.headers["cache-control"] == "public, max-age=31536000, immutable"
        assert served.headers["access-control-allow-origin"] == "*"
        assert client.get(f"/media/{DRAFT}").status_code == 404  # its slide is a draft
        assert client.get("/media/PHOTOS01/3-cccccccccccc.jpg").status_code == 404  # no such asset
        assert client.get("/media/../laminario.sqlite3").status_code == 404
        assert client.get("/media/PHOTOS01/..%2F..%2Flaminario.sqlite3").status_code == 404
