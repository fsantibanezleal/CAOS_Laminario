"""Derivatives: no GPS leaves the server, the true-scale mount, the scan placed on the macro photograph."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from app.imaging import derivatives, edf, reader

GPS_IFD = 0x8825


def photo_with_gps(path):
    image = Image.fromarray(np.random.default_rng(1).integers(0, 256, (600, 900, 3), dtype=np.uint8))
    exif = Image.Exif()
    exif[0x010F] = "Camera maker"
    gps = exif.get_ifd(GPS_IFD)
    gps[1] = "S"
    gps[2] = (33.0, 27.0, 0.0)
    gps[3] = "W"
    gps[4] = (70.0, 39.0, 0.0)
    image.save(path, exif=exif)
    assert GPS_IFD in Image.open(path).getexif()  # the input really carries a position


# R-018
def test_no_gps_in_served_files(vips, tmp_path):
    source = tmp_path / "field.jpg"
    photo_with_gps(source)
    image = vips.Image.new_from_file(str(source))
    written = list(derivatives.write_thumbnails(image, tmp_path / "out", "field").values())
    written.append(derivatives.save_clean(image, tmp_path / "out" / "full.webp"))
    written.append(derivatives.save_clean(image, tmp_path / "out" / "full.png"))
    for path in written:
        exif = Image.open(path).getexif()
        assert GPS_IFD not in exif and len(exif) == 0, path.name


def test_thumbnail_sides(vips, tmp_path):
    source = tmp_path / "field.jpg"
    photo_with_gps(source)
    thumbs = derivatives.write_thumbnails(vips.Image.new_from_file(str(source)), tmp_path, "field")
    assert Image.open(thumbs[320]).size == (320, 213)
    assert Image.open(thumbs[1024]).size == (900, 600)  # never enlarged


# R-019
@pytest.mark.parametrize("specimen_mm, rendered_px", [(12.0, 1500), (0.9, 1200), (40.0, 2400)])
def test_true_scale_mount(vips, specimen_mm, rendered_px):
    image = vips.Image.black(1000, 700, bands=3)
    mount = derivatives.true_scale_mount(image, specimen_mm, rendered_px)
    target = specimen_mm / derivatives.STANDARD_SLIDE_MM[0] * rendered_px
    assert abs(mount.width - target) <= max(0.01 * target, 0.5)  # whole pixels: half a pixel at most
    assert mount.height == round(700 * mount.width / 1000) or abs(mount.height - 700 * target / 1000) <= 1


# R-208
def test_scan_region_on_macro(vips, samples):
    info = reader.read_info(samples / "si_ostracod_A.ndpi")
    macro = reader.associated_image(info, "macro")
    box = derivatives.scan_region_on_macro(info, macro.width, macro.height)
    assert 0 < box.x < macro.width and 0 < box.y < macro.height
    grey = edf.luminance(reader.window(macro, 0, 0, macro.width, macro.height))
    x0, y0 = int(box.x), int(box.y)
    x1, y1 = int(np.ceil(box.x + box.width)), int(np.ceil(box.y + box.height))
    inside = np.percentile(grey[y0:y1, x0:x1], 5)
    ring = grey[y0 - 40:y1 + 40, x0 - 40:x1 + 40].copy()
    ring[40:40 + (y1 - y0), 40:40 + (x1 - x0)] = np.nan
    assert inside < np.nanpercentile(ring, 5) - 50  # measured 133 inside against 229 around
    rng = np.random.default_rng(0)  # same-size boxes over the cleared glass right of the label
    others = [np.percentile(grey[y:y + y1 - y0, x:x + x1 - x0], 5)
              for x, y in zip(rng.integers(650, 1750, 400), rng.integers(80, 560, 400), strict=True)]
    assert np.mean(np.array(others) <= inside) < 0.01
    assert derivatives.scan_region_on_macro(reader.read_info(samples / "cmu1.svs"), 1280, 431) is None
