"""IIIF delivery: info.json per asset, tiles equal to the pyramid, and the nginx site's cache and access check.

The first test uses a stand-in upstream shaped like iipsrv's own answer and runs everywhere. The others run
the pinned iipsrv (and nginx) containers and are skipped where no container engine is reachable; the unit's
verdict records the run on the production host.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import threading
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.imaging import pyramid
from app.main import create_app

from .support import (
    IIPSRV_IMAGE, NGINX_IMAGE, container, docker, free_port, json_body, make_settings, seed_slide, serve,
    wait_for_http,
)

ROOT = Path(__file__).resolve().parents[2]
CC_BY = "https://creativecommons.org/licenses/by/4.0/"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"


def iipsrv_info(key: str, width: int, height: int) -> dict:
    """What iipsrv 1.3 answers (captured from the pinned image), with the id it builds from the request."""
    return {"@context": "http://iiif.io/api/image/3/context.json", "protocol": "http://iiif.io/api/image",
            "width": width, "height": height, "sizes": [{"width": width // 4, "height": height // 4}],
            "tiles": [{"width": 512, "height": 512, "scaleFactors": [1, 2, 4, 8]}],
            "id": f"http://127.0.0.1:8149/iiif/{key}", "type": "ImageService3", "profile": "level2",
            "maxWidth": 5000, "maxHeight": 5000}


def asset(key: str, licence: str, **extra) -> dict:
    return {"family": "micro", "media_kind": "pyramid", "storage_key": key, "width_px": 3000, "height_px": 1700,
            "licence_uri": licence, "creator": "A. Contributor"} | extra


# R-021
def test_rights_rewritten_per_asset(tmp_path):
    keys = {"A1B2C3/0-3f9a.tif": CC_BY, "A1B2C3/1-77c1.tif": CC0, "D4E5F6/0-aa01.tif": CC_BY}
    routes = {f"/iiif/{k}/info.json": (200, {"Content-Type": "application/ld+json"},
                                       json_body(iipsrv_info(k, 3000, 1700))) for k in keys}
    with serve(routes) as upstream:
        settings = make_settings(tmp_path, iipsrv_url=upstream)
        seed_slide(settings, [asset(k, lic) for k, lic in list(keys.items())[:2]])
        seed_slide(settings, [asset("D4E5F6/0-aa01.tif", CC_BY)], publish=False)
        with TestClient(create_app(settings)) as client:
            for key, licence in list(keys.items())[:2]:
                encoded = key.replace("/", "%2F")
                response = client.get(f"/iiif/{encoded}/info.json")
                assert response.status_code == 200, response.text
                assert response.headers["content-type"].startswith("application/ld+json")
                assert response.headers["access-control-allow-origin"] == "*"
                info = response.json()
                assert info["rights"] == licence.replace("https://", "http://")
                assert info["id"] == f"https://laminario.example.org/iiif/{encoded}"
                assert info["width"] == 3000 and info["tiles"][0]["scaleFactors"] == [1, 2, 4, 8]
            assert client.get("/iiif/D4E5F6%2F0-aa01.tif/info.json").status_code == 404, "a draft is not served"
            assert client.get("/iiif/..%2F..%2Fetc%2Fpasswd/info.json").status_code == 404
            assert client.get("/iiif/A1B2C3%2F9-none.tif/info.json").status_code == 404
            redirect = client.get("/iiif/A1B2C3%2F0-3f9a.tif", follow_redirects=False)
            assert redirect.status_code == 303
            assert redirect.headers["location"] == "/iiif/A1B2C3%2F0-3f9a.tif/info.json"
            assert client.get("/api/_internal/iiif-access/A1B2C3/0-3f9a.tif").status_code == 204
            assert client.get("/api/_internal/iiif-access/D4E5F6/0-aa01.tif").status_code == 403


def test_image_parameters_are_validated(tmp_path):
    settings = make_settings(tmp_path)
    seed_slide(settings, [asset("A1/0.tif", CC_BY)])
    with TestClient(create_app(settings)) as client:
        # not a valid quality.format: read as a base URI with an unknown key
        assert client.get("/iiif/A1%2F0.tif/full/max/0/default.exe").status_code == 404


# --- with the pinned tile server ----------------------------------------------------------------------------


def textured(vips, width: int, height: int):
    """Structured content (gradients, edges, noise) so that tiles at every level differ."""
    noise = vips.Image.gaussnoise(width, height, sigma=18, mean=128)
    zone = vips.Image.zone(width, height) * 70 + 128
    xy = vips.Image.xyz(width, height)
    stripes = ((xy[0] // 37 + xy[1] // 53) % 2) * 120 + 60
    return noise.bandjoin([zone, stripes]).cast("uchar")


@pytest.fixture(scope="module")
def tile_server(tmp_path_factory, vips_module):
    exe = docker()
    store = tmp_path_factory.mktemp("store")
    os.chmod(store, 0o755)
    key = "T7EST0/0-5a5a.tif"
    target = store / key
    target.parent.mkdir(parents=True)
    image = textured(vips_module, 3000, 1700)
    written = pyramid.write_pyramid(image, target, 0.5)
    os.chmod(target, 0o644)
    os.chmod(target.parent, 0o755)
    port = free_port()
    name = f"laminario-test-iipsrv-{os.getpid()}"
    subprocess.run([exe, "pull", "-q", IIPSRV_IMAGE], capture_output=True, timeout=300)
    with container(["-p", f"127.0.0.1:{port}:80", "-v", f"{store}:/images:ro", IIPSRV_IMAGE], name):
        wait_for_http(f"http://127.0.0.1:{port}/iiif/{key}/info.json", expect=200)  # lighttpd answers first
        yield {"url": f"http://127.0.0.1:{port}", "store": store, "key": key, "file": target, "written": written,
               "name": name}


@pytest.fixture(scope="module")
def vips_module():
    try:
        from app.imaging.library import vips

        module = vips()
        module.version(0)
    except Exception as exc:
        pytest.skip(f"libvips is not available: {exc}")
    return module


def level_size(size: int, factor: int) -> int:
    """A side of a pyramid level: libvips halves each level from the one above, rounding down."""
    while factor > 1:
        size, factor = size // 2, factor // 2
    return size


def tile_requests(width: int, height: int, factors: list[int]):
    """(factor, level column, level row, region, size) for the corner, middle and edge tiles of each level."""
    for factor in factors:
        level_w, level_h = level_size(width, factor), level_size(height, factor)
        cols, rows = math.ceil(level_w / 512), math.ceil(level_h / 512)
        for col, row in {(0, 0), (cols - 1, 0), (0, rows - 1), (cols - 1, rows - 1), (cols // 2, rows // 2)}:
            tw, th = min(512, level_w - col * 512), min(512, level_h - row * 512)
            x, y = col * 512 * factor, row * 512 * factor
            w, h = min(tw * factor, width - x), min(th * factor, height - y)
            yield factor, col, row, f"{x},{y},{w},{h}", f"{tw},{th}"


# R-020
def test_tile_equals_crop(tmp_path, tile_server, vips_module):
    settings = make_settings(tmp_path, iipsrv_url=tile_server["url"])
    seed_slide(settings, [asset(tile_server["key"], CC_BY)])
    encoded = tile_server["key"].replace("/", "%2F")
    with TestClient(create_app(settings)) as client:
        info = client.get(f"/iiif/{encoded}/info.json").json()
        assert (info["width"], info["height"]) == (3000, 1700)
        factors = info["tiles"][0]["scaleFactors"]
        assert factors == [1, 2, 4, 8]
        checked = 0
        for factor, col, row, region, size in tile_requests(3000, 1700, factors):
            response = client.get(f"/iiif/{encoded}/{region}/{size}/0/default.png")
            assert response.status_code == 200, (region, size, response.text[:200])
            served = np.asarray(Image.open(__import__("io").BytesIO(response.content)).convert("RGB"), dtype=int)
            page = int(math.log2(factor))
            level = vips_module.Image.tiffload(str(tile_server["file"]), page=page)
            th, tw = served.shape[:2]
            region_pixels = level.crop(col * 512, row * 512, tw, th)
            expected = np.ndarray(buffer=region_pixels.write_to_memory(), dtype=np.uint8,
                                  shape=(th, tw, region_pixels.bands)).astype(int)
            difference = np.abs(served - expected).max()
            assert difference <= 2, f"factor {factor} tile {col},{row}: max difference {difference}"
            checked += 1
        assert checked >= 16


# R-301
def test_nginx_caches_tiles_and_refuses_unpublished(tmp_path, tile_server):
    """The production site file, run by the pinned nginx on the host network as on the production host.

    Host networking puts nginx, the API and iipsrv on loopback, the production topology; it needs a Linux
    container engine (on Docker Desktop the "host" is the virtual machine).
    """
    exe = docker()
    if sys.platform != "linux":
        pytest.skip("host networking for the nginx container needs a Linux container engine")
    api_port, nginx_port = free_port(), free_port()
    iip_port = int(tile_server["url"].rsplit(":", 1)[1])
    settings = make_settings(tmp_path, iipsrv_url=tile_server["url"])
    seed_slide(settings, [asset(tile_server["key"], CC_BY)])
    draft_key = "T7EST0/1-draft.tif"
    seed_slide(settings, [asset(draft_key, CC_BY)], publish=False)

    import httpx2
    import uvicorn

    server = uvicorn.Server(uvicorn.Config(create_app(settings), host="127.0.0.1", port=api_port,
                                           log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        wait_for_http(f"http://127.0.0.1:{api_port}/api/health", expect=200)
        conf = (ROOT / "deploy" / "nginx" / "laminario.conf").read_text(encoding="utf-8")
        conf = (conf.replace("server 127.0.0.1:8147;", f"server 127.0.0.1:{api_port};")
                .replace("server 127.0.0.1:8149;", f"server 127.0.0.1:{iip_port};")
                .replace("/srv/laminario/cache", "/var/cache/laminario")
                .replace("    listen 80;", f"    listen 127.0.0.1:{nginx_port};")
                .replace("    listen [::]:80;", ""))
        assert f"listen 127.0.0.1:{nginx_port};" in conf
        conf_file = tmp_path / "laminario.conf"
        conf_file.write_text(conf, encoding="utf-8")
        os.chmod(conf_file, 0o644)
        empty = tmp_path / "empty.conf"
        empty.write_text("", encoding="utf-8")  # replaces the image's default site, which listens on port 80
        os.chmod(empty, 0o644)
        subprocess.run([exe, "pull", "-q", NGINX_IMAGE], capture_output=True, timeout=300)
        with container(["--network", "host", "-v", f"{conf_file}:/etc/nginx/conf.d/laminario.conf:ro",
                        "-v", f"{empty}:/etc/nginx/conf.d/default.conf:ro", "--tmpfs", "/var/cache/laminario",
                        NGINX_IMAGE], f"laminario-test-nginx-{os.getpid()}"):
            base = f"http://127.0.0.1:{nginx_port}"
            wait_for_http(base + "/api/health", expect=200)
            encoded = tile_server["key"].replace("/", "%2F")
            tile = f"{base}/iiif/{encoded}/0,0,1024,1024/512,/0/default.jpg"
            first, second = httpx2.get(tile, timeout=30), httpx2.get(tile, timeout=30)
            assert first.status_code == second.status_code == 200, first.text[:200]
            assert (first.headers["x-cache-status"], second.headers["x-cache-status"]) == ("MISS", "HIT")
            assert first.content == second.content
            assert first.headers["access-control-allow-origin"] == "*"
            direct = httpx2.get(f"{tile_server['url']}/iiif/{tile_server['key']}/0,0,1024,1024/512,/0/default.jpg",
                                timeout=30)
            assert first.content == direct.content, "nginx serves iipsrv's bytes"
            draft = httpx2.get(f"{base}/iiif/{draft_key.replace('/', '%2F')}/full/256,/0/default.jpg", timeout=30)
            assert draft.status_code == 403, "an unpublished image is refused before the cache"
            info = httpx2.get(f"{base}/iiif/{encoded}/info.json", timeout=30)
            assert info.status_code == 200 and info.json()["rights"] == "http://creativecommons.org/licenses/by/4.0/"
            hidden = httpx2.get(f"{base}/api/_internal/iiif-access/{tile_server['key']}", timeout=30)
            assert hidden.status_code == 404, "the access check is not reachable from outside"
    finally:
        server.should_exit = True
        thread.join(10)
