"""Limits applied from headers, before any pixel is decoded.

A decompression bomb is a small file that expands to an image far larger than the machine can hold; the
limits below are the product's stated maxima (200,000 px per side, 20 gigapixels per plane) and match the
ingestion contract's ranges.
"""

from __future__ import annotations

MAX_SIDE_PX = 200_000
MAX_PLANE_PX = 20_000_000_000
MIN_SIDE_PX = 64


class ImageRefused(ValueError):
    """The image breaks a limit and was not decoded."""

    def __init__(self, field: str, message: str, expected: str):
        super().__init__(f"{field}: {message} (expected {expected})")
        self.field = field
        self.message = message
        self.expected = expected


def check_dimensions(width: int, height: int) -> None:
    """Raise ``ImageRefused`` when a plane's header dimensions break a limit."""
    if width < MIN_SIDE_PX or height < MIN_SIDE_PX:
        raise ImageRefused("dimensions", f"{width} x {height} px is too small", f"at least {MIN_SIDE_PX} px per side")
    if width > MAX_SIDE_PX or height > MAX_SIDE_PX:
        raise ImageRefused("dimensions", f"{width} x {height} px exceeds the side limit",
                           f"at most {MAX_SIDE_PX} px per side")
    if width * height > MAX_PLANE_PX:
        raise ImageRefused("dimensions", f"{width * height / 1e9:.1f} gigapixels exceeds the plane limit",
                           f"at most {MAX_PLANE_PX / 1e9:.0f} gigapixels per plane")
