"""The reader against the vendor metadata of every fixture format."""

from __future__ import annotations

import pytest

from app.imaging import reader
from app.imaging.library import info as library_info

# Values read from each file's own vendor metadata (OpenSlide properties, Hamamatsu tags, TIFF tags).
EXPECTED = {
    "cmu1.svs": dict(loader="openslide", vendor="aperio", width=46000, height=32914,
                     level_widths=[46000, 11500, 2875], mpp=0.499, objective=20.0,
                     associated={"label", "macro", "thumbnail"}, planes=1),
    "si_ostracod_A.ndpi": dict(loader="openslide", vendor="hamamatsu", width=3840, height=4608,
                               level_widths=[3840, 1920, 960, 480, 240, 120, 60], mpp=0.228859,
                               objective=40.0, associated={"macro"}, planes=71),
    "nhm_lice_scan.tif": dict(loader="tiff", vendor=None, width=7369, height=3377, level_widths=[7369],
                              mpp=None, objective=None, associated=set(), planes=1),
    "commons_thin_xpl.jpg": dict(loader="jpeg", vendor=None, width=4010, height=2100, level_widths=[4010],
                                 mpp=None, objective=None, associated=set(), planes=1),
}


# R-010
@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_fixture_matrix_metadata(vips, samples, name):
    expected = EXPECTED[name]
    info = reader.read_info(samples / name)
    assert info.loader == expected["loader"]
    assert info.vendor == expected["vendor"]
    assert (info.width, info.height) == (expected["width"], expected["height"])
    assert [level.width for level in info.levels] == expected["level_widths"]
    if expected["mpp"] is None:
        assert info.mpp_x is None and info.mpp_source is None
    else:
        assert info.mpp_x == pytest.approx(expected["mpp"], rel=1e-5)
        assert info.mpp_source == "vendor"
    assert info.objective_power == expected["objective"]
    assert set(info.associated) == expected["associated"]
    assert len(info.planes) == expected["planes"]


def test_ndpi_focal_planes_and_slide_geometry(vips, samples):
    info = reader.read_info(samples / "si_ostracod_A.ndpi")
    depths = [plane.depth_um for plane in info.planes]
    assert depths[0] == -70.0 and depths[-1] == 70.0
    assert all(b - a == pytest.approx(2.0) for a, b in zip(depths, depths[1:], strict=False))
    assert info.slide_size_mm == (76.0, 26.0)
    assert info.scan_centre_offset_mm == pytest.approx((3.2268, 0.8418))
    first, last = reader.open_plane(info, 0), reader.open_plane(info, 70)
    assert (first.width, first.height, first.bands) == (3840, 4608, 3)
    assert reader.window(first, 1500, 2000, 256, 256).mean() != reader.window(last, 1500, 2000, 256, 256).mean()


def test_imagej_stack_planes(vips, edf_reference):
    info = reader.read_info(edf_reference / "dome" / "stack.tif")
    assert len(info.planes) == 20
    assert info.mpp_x is None  # 75 dpi in inches is a screen default, not a calibration
    plane = reader.open_plane(info, 19)
    assert (plane.width, plane.height, plane.bands) == (499, 363, 3)


# R-201
def test_associated_images_exposed(vips, samples):
    svs = reader.read_info(samples / "cmu1.svs")
    sizes = {name: reader.associated_image(svs, name) for name in svs.associated}
    assert (sizes["label"].width, sizes["label"].height) == (387, 463)
    assert (sizes["macro"].width, sizes["macro"].height) == (1280, 431)
    assert all(image.bands == 3 for image in sizes.values())
    ndpi = reader.read_info(samples / "si_ostracod_A.ndpi")
    macro = reader.associated_image(ndpi, "macro")
    assert (macro.width, macro.height) == (1896, 647)
    with pytest.raises(KeyError):
        reader.associated_image(ndpi, "label")


# R-203
def test_library_loads_with_openslide(vips):
    found = library_info()
    assert found.openslide, "this libvips build cannot read scanner formats"
    major, minor, _ = (int(part) for part in found.version.split("."))
    assert (major, minor) >= (8, 15)  # keep= metadata control used by every writer


def test_an_ndpi_plane_from_its_jpeg_stream_is_the_plane_libtiff_reads(vips, samples):
    """Past 4 GB an NDPI file's planes are out of libtiff's reach (F-041); the reader then decodes the plane from its
    own JPEG stream. Where libtiff can read the plane too, both routes give the same pixels."""
    info = reader.read_info(samples / "si_ostracod_A.ndpi")
    for plane in (info.planes[0], info.planes[-1]):
        streamed = reader._ndpi_stream(info.path, plane.page)
        direct = vips.Image.tiffload(info.path, page=plane.page, unlimited=True)
        assert (streamed.width, streamed.height) == (direct.width, direct.height) == (3840, 4608)
        for x, y in ((0, 0), (1600, 2000), (3328, 4096)):
            assert (streamed.crop(x, y, 512, 512) - direct.crop(x, y, 512, 512)).abs().max() == 0
