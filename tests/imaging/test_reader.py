"""The reader against the vendor metadata of every fixture format."""

from __future__ import annotations

from pathlib import Path

import numpy as np
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


def _restart_jpeg(vips, pixels: np.ndarray, interval_mcus: int, subsample: str):
    """A JPEG with a restart marker every ``interval_mcus`` MCUs, split as a Hamamatsu file stores its intervals: the
    header up to the scan header, and each interval's bytes with its trailing marker."""
    image = vips.Image.new_from_memory(np.ascontiguousarray(pixels).tobytes(), pixels.shape[1], pixels.shape[0], 3,
                                       "uchar")
    data = image.jpegsave_buffer(Q=90, restart_interval=interval_mcus, subsample_mode=subsample)
    sos = data.index(b"\xff\xda")
    start = sos + 2 + int.from_bytes(data[sos + 2:sos + 4], "big")
    chunks, at = [], start
    for i in range(start, len(data) - 1):
        if data[i] == 0xFF and 0xD0 <= data[i + 1] <= 0xD9:
            chunks.append(data[at:i + 2])
            at = i + 2
    return data, data[:start], chunks


def test_a_jpeg_decoded_by_its_restart_intervals_equals_the_whole(vips):
    """A Hamamatsu plane beyond libjpeg's size is decoded as a mosaic of JPEGs made from its restart intervals: the
    same pixels as the whole JPEG, across tiles whose restart markers are numbered again (R-001)."""
    rng = np.random.default_rng(7)
    ys, xs = np.mgrid[0:96, 0:160]
    base = (128 + 60 * np.sin(xs / 9.0) * np.cos(ys / 7.0))[..., None] + rng.normal(0, 12, (96, 160, 3))
    pixels = np.clip(base, 0, 255).astype(np.uint8)
    whole, header, chunks = _restart_jpeg(vips, pixels, 5, "off")  # 4:4:4: an interval is 8 x 40 px
    assert len(chunks) == 12 * 4
    expected = np.asarray(reader.window(vips.Image.jpegload_buffer(whole), 0, 0, 160, 96))
    for band, across in ((16, 80), (24, 120), (96, 160), (8, 40)):
        mosaic = reader.intervals_mosaic(header, chunks, (8, 40), (12, 4), band=band, across=across)
        assert (mosaic.width, mosaic.height) == (160, 96)
        assert np.array_equal(np.asarray(reader.window(mosaic, 0, 0, 160, 96)), expected), (band, across)

    whole, header, chunks = _restart_jpeg(vips, pixels, 5, "on")  # 4:2:0: an interval is 16 x 80 px
    expected = np.asarray(reader.window(vips.Image.jpegload_buffer(whole), 0, 0, 160, 96)).astype(int)
    mosaic = reader.intervals_mosaic(header, chunks, (16, 80), (6, 2), band=32, across=80)
    got = np.asarray(reader.window(mosaic, 0, 0, 160, 96)).astype(int)
    assert np.abs(got - expected).mean() < 1.0  # only the tiles' edges can differ, by the chroma upsampling


def test_a_single_colour_is_told_from_an_image(vips):
    flat = vips.Image.black(64, 48, bands=3) + [10, 20, 30]
    assert reader.single_colour(flat)
    assert reader.single_colour(vips.Image.black(64, 48))
    dotted = flat.draw_rect([10, 20, 31], 5, 5, 1, 1)
    assert not reader.single_colour(dotted)


def _large_ndpi(fixtures: Path):
    import json

    from app.base.acquire import ACQUIRED

    acquired = json.loads(ACQUIRED.read_text(encoding="utf-8"))
    for got in acquired.values():
        path = fixtures / "base" / "sources" / got.get("open", got["file"])
        if path.suffix.lower() == ".ndpi" and path.is_file() and path.stat().st_size > 1_000_000_000:
            info = reader.read_info(path)
            if max(info.width, info.height) > reader.JPEG_MAX_SIDE and len(info.planes) > 1:
                return info
    return None


def test_a_hamamatsu_plane_beyond_the_jpeg_limit_reads_as_openslide_does(fixtures: Path, vips):
    """A Zenodo NDPI of 53,760 x 73,728 px with three planes: libtiff returned every plane black, without an error.
    Read by its intervals, the plane at depth 0 equals OpenSlide's level 0 (the scanner's default plane), across the
    mosaic's seams, and the others are images of their own."""
    info = _large_ndpi(fixtures)
    if info is None:
        pytest.skip("no acquired Hamamatsu stack beyond the JPEG limit in the vault")
    default = next(i for i, p in enumerate(info.planes) if p.depth_um == 0)
    slide = reader._flatten(vips.Image.openslideload(info.path, level=0))
    spots = [(info.width // 3, info.height // 3), (info.width // 2, 1024 * 24 - 256)]
    for plane in range(len(info.planes)):
        image = reader.open_plane(info, plane)
        assert (image.width, image.height, image.bands) == (info.width, info.height, 3)
        for x, y in spots:
            got = np.asarray(reader.window(image, x, y, 512, 512))
            assert got.std() > 1.0, (plane, x, y)
            if plane == default:
                assert np.array_equal(got, np.asarray(reader.window(slide, x, y, 512, 512)))
