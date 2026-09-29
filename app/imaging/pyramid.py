"""One tiled, pyramidal BigTIFF per plane: what the tile server reads.

``tiffsave(tile=True, pyramid=True, bigtiff=True)`` with 512 px tiles writes level 0 and every half-size level
below it until the image fits one tile, so a plane of long side ``n`` has ``ceil(log2(n / 512)) + 1`` levels.

Quality is measured, not assumed. Tiles are JPEG at quality 85; the mean peak signal-to-noise ratio of level
0 against the source over 32 seeded 512 px regions must reach 38 dB. At quality 85 libvips subsamples
chroma (4:2:0), which is transparent for most specimens but not for colour-dense textures such as a thin
section under crossed polars, whose interference colours are the diagnostic content (the Commons thin
section: 32.1 dB). When quality 85 falls short, the plane is written again at quality 90, where libvips keeps
full chroma (49.9 dB on the same image, 2.9 times the bytes), and if that still falls short, at quality 95
(content close to pure noise); the last file is kept with its measured PSNR, which the worker records on the
asset. WebP at quality 80 is tried when asked and kept only when its file is smaller than the JPEG file and it
also reaches the floor.

When the pixel size is known it goes into the TIFF resolution tags (pixels per centimetre, unit
centimetre), so any TIFF viewer shows the right scale; when it is not known the resolution unit is set to
"none", so no viewer shows a scale copied from a camera's or a screen's nominal dpi. Metadata other than
the ICC profile is not copied, so no EXIF leaves the server.
"""

from __future__ import annotations

import gc
import math
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.imaging.library import vips
from app.imaging.reader import window

TILE = 512
JPEG_QUALITY = 85
JPEG_FULL_CHROMA_QUALITY = 90
JPEG_LAST_QUALITY = 95
#: Qualities tried in order until level 0 reaches the floor; the last one is kept, with its PSNR, if none does.
JPEG_LADDER = (JPEG_QUALITY, JPEG_FULL_CHROMA_QUALITY, JPEG_LAST_QUALITY)
WEBP_QUALITY = 80
MIN_PSNR_DB = 38.0
FIDELITY_REGIONS = 32
FIDELITY_SEED = 20260924
RESUNIT_NONE = 1


@dataclass(frozen=True)
class PyramidFile:
    path: str
    codec: str
    quality: int
    bytes: int
    width: int
    height: int
    levels: int
    psnr_db: float


def level_count(width: int, height: int, tile: int = TILE) -> int:
    """Levels from full size down to the first that fits one tile."""
    longest = max(width, height)
    return 1 if longest <= tile else math.ceil(math.log2(longest / tile)) + 1


def region_origins(width: int, height: int, count: int = FIDELITY_REGIONS, size: int = TILE,
                   seed: int = FIDELITY_SEED) -> list[tuple[int, int]]:
    """``count`` region corners, seeded, fully inside the image."""
    rng = np.random.default_rng(seed)
    xs = rng.integers(0, max(width - size, 0) + 1, count)
    ys = rng.integers(0, max(height - size, 0) + 1, count)
    return [(int(x), int(y)) for x, y in zip(xs, ys, strict=True)]


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = float(np.mean((a.astype(np.float64) - b.astype(np.float64)) ** 2))
    return math.inf if mse == 0 else 10 * math.log10(255.0**2 / mse)


def level0_psnr(source, written, count: int = FIDELITY_REGIONS, size: int = TILE,
                seed: int = FIDELITY_SEED) -> float:
    """Mean PSNR over seeded regions of the source and of the written file's level 0 (libvips images)."""
    w, h = min(size, source.width), min(size, source.height)
    values = [psnr(window(source, x, y, w, h), window(written, x, y, w, h))
              for x, y in region_origins(source.width, source.height, count, size, seed)]
    finite = [v for v in values if math.isfinite(v)]
    return float(np.mean(finite)) if finite else math.inf


def _clear_resolution_unit(path: Path) -> None:
    import tifffile

    with tifffile.TiffFile(str(path), mode="r+b") as tif:
        for page in tif.pages:
            tag = page.tags.get("ResolutionUnit")
            if tag is not None:
                tag.overwrite(RESUNIT_NONE)


def _save(image, path: Path, codec: str, quality: int, mpp_um: float | None, tile: int) -> None:
    options = dict(tile=True, pyramid=True, bigtiff=True, tile_width=tile, tile_height=tile, keep="icc",
                   compression=codec, Q=quality)
    if mpp_um:
        px_per_mm = 1000.0 / mpp_um
        options |= dict(xres=px_per_mm, yres=px_per_mm, resunit="cm")
    image.tiffsave(str(path), **options)
    if not mpp_um:
        _clear_resolution_unit(path)


def _measure(image, path: Path) -> float:
    """PSNR of a written file, then every handle on it released (Windows cannot replace an open file)."""
    module = vips()
    written = module.Image.new_from_file(str(path))
    score = level0_psnr(image, written)
    del written
    previous = module.cache_get_max()
    module.cache_set_max(0)  # drops cached operations, which hold the file open
    module.cache_set_max(previous)
    gc.collect()
    return score


def _write_measured(image, path: Path, codec: str, quality: int, mpp_um: float | None, tile: int) -> PyramidFile:
    _save(image, path, codec, quality, mpp_um, tile)
    score = _measure(image, path)
    return PyramidFile(str(path), codec, quality, path.stat().st_size, image.width, image.height,
                       level_count(image.width, image.height, tile), score)


def write_pyramid(image, path: str | Path, mpp_um: float | None = None, codec: str = "jpeg",
                  tile: int = TILE, min_psnr_db: float = MIN_PSNR_DB) -> PyramidFile:
    """Write ``image`` (a libvips image, 8-bit) as a pyramidal BigTIFF that reaches the fidelity floor.

    ``codec`` is ``jpeg``, ``webp`` or ``auto``; ``auto`` keeps WebP only when it is smaller than the JPEG
    file and also reaches the floor.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if image.format != "uchar":
        image = image.cast("uchar")
    if codec == "webp":
        return _write_measured(image, path, "webp", WEBP_QUALITY, mpp_um, tile)
    if codec not in ("jpeg", "auto"):
        raise ValueError(f"unknown codec {codec!r}")
    for quality in JPEG_LADDER:
        result = _write_measured(image, path, "jpeg", quality, mpp_um, tile)
        if result.psnr_db >= min_psnr_db:
            break
    if codec == "jpeg":
        return result
    candidate = path.with_name(path.stem + ".webp-candidate" + path.suffix)
    webp = _write_measured(image, candidate, "webp", WEBP_QUALITY, mpp_um, tile)
    if webp.bytes < result.bytes and webp.psnr_db >= min_psnr_db:
        os.replace(candidate, path)
        return PyramidFile(str(path), "webp", webp.quality, webp.bytes, webp.width, webp.height, webp.levels,
                           webp.psnr_db)
    candidate.unlink()
    return result
