"""Decompression bombs are refused from the header, before any pixel is decoded."""

from __future__ import annotations

import struct

import pytest

from app.imaging import guards, reader


def tiff_header(path, width, height):
    """A minimal baseline TIFF claiming ``width`` x ``height`` grey pixels, holding one byte of data.

    Decoding it would fail; a refusal therefore proves the limit was applied from the header.
    """
    entries = [
        (256, 4, 1, width),  # ImageWidth, LONG
        (257, 4, 1, height),  # ImageLength
        (258, 3, 1, 8),  # BitsPerSample, SHORT
        (259, 3, 1, 1),  # Compression: none
        (262, 3, 1, 1),  # Photometric: black is zero
        (273, 4, 1, 0),  # StripOffsets, patched below
        (277, 3, 1, 1),  # SamplesPerPixel
        (278, 4, 1, height),  # RowsPerStrip
        (279, 4, 1, 1),  # StripByteCounts
    ]
    ifd_size = 2 + 12 * len(entries) + 4
    data_offset = 8 + ifd_size
    body = struct.pack("<H", len(entries))
    for tag, kind, count, value in entries:
        value = data_offset if tag == 273 else value
        packed = struct.pack("<HHI", tag, kind, count)
        body += packed + (struct.pack("<HH", value, 0) if kind == 3 else struct.pack("<I", value))
    path.write_bytes(b"II*\x00" + struct.pack("<I", 8) + body + struct.pack("<I", 0) + b"\x00")


# R-017
@pytest.mark.parametrize(
    "width, height, expected",
    [(200_001, 64, "side"), (64, 250_000, "side"), (150_000, 150_000, "plane")],
)
def test_decompression_bomb_refused(vips, tmp_path, width, height, expected):
    path = tmp_path / f"bomb-{width}x{height}.tif"
    tiff_header(path, width, height)
    with pytest.raises(guards.ImageRefused) as refused:
        reader.read_info(path)
    assert refused.value.field == "dimensions"
    assert expected in refused.value.message


def test_limits_in_numbers():
    guards.check_dimensions(200_000, 100_000)  # 20 gigapixels exactly is allowed
    with pytest.raises(guards.ImageRefused):
        guards.check_dimensions(200_000, 100_001)
    with pytest.raises(guards.ImageRefused):
        guards.check_dimensions(63, 1000)
