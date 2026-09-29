"""The pyramid writer: structure, fidelity, resolution tags and the codec rule."""

from __future__ import annotations

import pytest
import tifffile

from app.imaging import pyramid, reader

CMU1_REGION = (12000, 8000, 6000, 5000)  # a 30 MP region of tissue keeps the test fast


def cmu1_region(samples):
    info = reader.read_info(samples / "cmu1.svs")
    return info, reader.open_plane(info).crop(*CMU1_REGION)


def synthetic(vips, width=3000, height=1700):
    """A textured RGB image built by libvips itself: runs wherever libvips does, no fixtures needed."""
    noise = vips.Image.gaussnoise(width, height, sigma=40, mean=128)
    zone = vips.Image.zone(width, height) * 60 + 128
    return noise.bandjoin([zone, (noise + zone) / 2]).cast("uchar")


# R-011
def test_level_structure(vips, tmp_path):
    image = synthetic(vips)
    out = pyramid.write_pyramid(image, tmp_path / "plane.tif")
    with tifffile.TiffFile(out.path) as tif:
        assert tif.is_bigtiff
        pages = tif.pages
        assert len(pages) == out.levels == pyramid.level_count(3000, 1700) == 4
        widths = [p.shape[1] for p in pages]
        assert widths[0] == 3000 and all(w <= 512 for w in widths[-1:])
        assert all(p.tags["TileWidth"].value == 512 and p.tags["TileLength"].value == 512 for p in pages)
        for bigger, smaller in zip(widths, widths[1:], strict=False):
            assert smaller in (bigger // 2, (bigger + 1) // 2)


def test_level_count_formula():
    assert pyramid.level_count(512, 300) == 1
    assert pyramid.level_count(513, 300) == 2
    assert pyramid.level_count(46000, 32914) == 8
    assert pyramid.level_count(3840, 4608) == 5


# R-012
@pytest.mark.parametrize("name", ["cmu1.svs", "nhm_lice_scan.tif", "commons_thin_xpl.jpg"])
def test_level0_fidelity(vips, samples, tmp_path, name):
    info = reader.read_info(samples / name)
    image = reader.open_plane(info)
    if name == "cmu1.svs":
        image = image.crop(*CMU1_REGION)
    out = pyramid.write_pyramid(image, tmp_path / "plane.tif", info.mpp_x)
    assert out.psnr_db >= 38.0
    written = vips.Image.new_from_file(out.path)
    assert pyramid.level0_psnr(image, written) == pytest.approx(out.psnr_db)
    if name == "commons_thin_xpl.jpg":
        assert out.quality == pyramid.JPEG_FULL_CHROMA_QUALITY  # 4:2:0 at Q85 measured 32.1 dB here
    else:
        assert out.quality == pyramid.JPEG_QUALITY


# R-013
def test_resolution_tags(vips, samples, tmp_path):
    info, image = cmu1_region(samples)
    out = pyramid.write_pyramid(image, tmp_path / "calibrated.tif", info.mpp_x)
    with tifffile.TiffFile(out.path) as tif:
        tags = tif.pages[0].tags
        assert tags["ResolutionUnit"].value == tifffile.RESUNIT.CENTIMETER
        numerator, denominator = tags["XResolution"].value
        assert 1e4 / (numerator / denominator) == pytest.approx(0.499, rel=1e-4)
    uncalibrated = pyramid.write_pyramid(synthetic(vips, 800, 600), tmp_path / "uncalibrated.tif")
    with tifffile.TiffFile(uncalibrated.path) as tif:
        assert {int(p.tags["ResolutionUnit"].value) for p in tif.pages} == {pyramid.RESUNIT_NONE}


# R-202
@pytest.mark.parametrize("name", ["nhm_lice_scan.tif", "commons_thin_xpl.jpg"])
def test_webp_kept_only_when_smaller(vips, samples, tmp_path, name):
    info = reader.read_info(samples / name)
    image = reader.open_plane(info)
    jpeg = pyramid.write_pyramid(image, tmp_path / "jpeg.tif", codec="jpeg")
    webp = pyramid.write_pyramid(image, tmp_path / "webp.tif", codec="webp")
    chosen = pyramid.write_pyramid(image, tmp_path / "auto.tif", codec="auto")
    if webp.bytes < jpeg.bytes and webp.psnr_db >= pyramid.MIN_PSNR_DB:
        assert chosen.codec == "webp" and chosen.bytes == webp.bytes
    else:
        assert chosen.codec == "jpeg" and chosen.bytes == jpeg.bytes
    assert not list(tmp_path.glob("*webp-candidate*"))
