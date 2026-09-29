"""The basemap endpoint: the PMTiles file with byte ranges, or a 404 the map can draw without."""

from __future__ import annotations

from tests.accounts.support import app_client, settings_for


def test_the_basemap_is_served_by_byte_ranges(tmp_path):
    archive = tmp_path / "world.pmtiles"
    archive.write_bytes(bytes(range(256)) * 16)
    settings = settings_for(tmp_path).model_copy(update={"basemap": archive})
    with app_client(settings) as client:
        part = client.get("/api/explore/basemap.pmtiles", headers={"Range": "bytes=127-254"})
        assert part.status_code == 206
        assert part.content == bytes(range(127, 255))
        assert part.headers["content-range"] == "bytes 127-254/4096"
        assert client.get("/api/explore/basemap.pmtiles").content == archive.read_bytes()


def test_a_missing_basemap_is_a_404(tmp_path):
    with app_client(settings_for(tmp_path)) as client:
        assert client.get("/api/explore/basemap.pmtiles").status_code == 404
