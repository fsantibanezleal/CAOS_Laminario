"""The small images the interface shows, written without metadata that could reveal a place.

- Thumbnails at 320 and 1024 px on the long side, JPEG quality 80.
- The scanned region on the scanner's macro photograph: for a Hamamatsu file, the vendor tags give the
  slide's size and the scan's centre as an offset from the slide centre (x to the right, y downwards, in
  nanometres); with the pixel size and the scan's pixel dimensions this places the scan on the macro
  photograph, so the slide object can show where on the real glass the specimen sits.
- The crop under the coverslip: on a contributor's photograph of the whole slide, the box the coverslip
  occupies, from the slide's and the coverslip's sizes in the slide case (centred unless an offset is given).
- The true-scale mount: the specimen image scaled so that, drawn on a rendered slide, it spans its physical
  width divided by the slide's width.

Every file is written with ``keep="icc"``: the colour profile stays, EXIF (with any GPS position), XMP and
IPTC do not.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.imaging.reader import SlideInfo

THUMBNAIL_SIDES = (320, 1024)
THUMBNAIL_QUALITY = 80
STANDARD_SLIDE_MM = (75.0, 25.0)  # ISO 8037-1 microscope slide, 75 x 25 mm


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float


def save_clean(image, path: str | Path, quality: int = THUMBNAIL_QUALITY) -> Path:
    """Write an image with its colour profile only; the format follows the file suffix."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        image.jpegsave(str(path), Q=quality, keep="icc")
    elif suffix == ".webp":
        image.webpsave(str(path), Q=quality, keep="icc")
    elif suffix == ".png":
        image.pngsave(str(path), keep="icc")
    else:
        raise ValueError(f"derivatives are JPEG, WebP or PNG, not {suffix}")
    return path


def thumbnail(image, long_side: int):
    """The image scaled so its long side is ``long_side`` px (never enlarged)."""
    if max(image.width, image.height) <= long_side:
        return image
    return image.thumbnail_image(long_side, height=long_side, size="down")


def write_thumbnails(image, folder: str | Path, stem: str) -> dict[int, Path]:
    return {side: save_clean(thumbnail(image, side), Path(folder) / f"{stem}-{side}.jpg") for side in THUMBNAIL_SIDES}


def scan_region_on_macro(info: SlideInfo, macro_width: int, macro_height: int) -> Box | None:
    """Where the scanned region sits on the macro photograph, in macro pixels; None without vendor geometry."""
    if not (info.slide_size_mm and info.scan_centre_offset_mm and info.mpp_x and info.mpp_y):
        return None
    slide_w, slide_h = info.slide_size_mm
    px_per_mm_x, px_per_mm_y = macro_width / slide_w, macro_height / slide_h
    scan_w_mm = info.width * info.mpp_x / 1000.0
    scan_h_mm = info.height * info.mpp_y / 1000.0
    centre_x = (slide_w / 2 + info.scan_centre_offset_mm[0]) * px_per_mm_x
    centre_y = (slide_h / 2 + info.scan_centre_offset_mm[1]) * px_per_mm_y
    return Box(centre_x - scan_w_mm * px_per_mm_x / 2, centre_y - scan_h_mm * px_per_mm_y / 2,
               scan_w_mm * px_per_mm_x, scan_h_mm * px_per_mm_y)


def coverslip_region(photo_width: int, photo_height: int, slide_mm: tuple[float, float],
                     coverslip_mm: tuple[float, float],
                     centre_offset_mm: tuple[float, float] = (0.0, 0.0)) -> Box:
    """The coverslip's box on a photograph of the whole slide, in photo pixels.

    The photograph spans the slide (the contributor crops it to the glass); either orientation. Sizes are
    (long side, short side) in millimetres, the coverslip's long side along the slide's; the coverslip is
    centred unless an offset from the slide centre is given, in the photograph's own axes: along its long
    side, then its short side, positive towards increasing pixel index.
    """
    long_px, short_px = max(photo_width, photo_height), min(photo_width, photo_height)
    per_mm_long, per_mm_short = long_px / slide_mm[0], short_px / slide_mm[1]
    box_long, box_short = coverslip_mm[0] * per_mm_long, coverslip_mm[1] * per_mm_short
    centre_long = long_px / 2 + centre_offset_mm[0] * per_mm_long
    centre_short = short_px / 2 + centre_offset_mm[1] * per_mm_short
    if photo_width >= photo_height:
        return Box(centre_long - box_long / 2, centre_short - box_short / 2, box_long, box_short)
    return Box(centre_short - box_short / 2, centre_long - box_long / 2, box_short, box_long)


def coverslip_crop(image, slide_mm: tuple[float, float], coverslip_mm: tuple[float, float],
                   centre_offset_mm: tuple[float, float] = (0.0, 0.0)):
    """The part of a slide photograph under the coverslip, clipped to the photograph."""
    box = coverslip_region(image.width, image.height, slide_mm, coverslip_mm, centre_offset_mm)
    x0, y0 = max(0, round(box.x)), max(0, round(box.y))
    x1 = min(image.width, round(box.x + box.width))
    y1 = min(image.height, round(box.y + box.height))
    return image.crop(x0, y0, x1 - x0, y1 - y0)


def mount_width_px(specimen_width_mm: float, rendered_slide_width_px: float,
                   slide_width_mm: float = STANDARD_SLIDE_MM[0]) -> float:
    """Width in rendered pixels that a specimen of a given physical width occupies on the drawn slide."""
    if specimen_width_mm <= 0 or slide_width_mm <= 0:
        raise ValueError("widths must be positive")
    return specimen_width_mm / slide_width_mm * rendered_slide_width_px


def true_scale_mount(image, specimen_width_mm: float, rendered_slide_width_px: float,
                     slide_width_mm: float = STANDARD_SLIDE_MM[0]):
    """The specimen image resized to its true-scale width on a slide drawn ``rendered_slide_width_px`` wide."""
    target = max(1, round(mount_width_px(specimen_width_mm, rendered_slide_width_px, slide_width_mm)))
    return image.resize(target / image.width, kernel="lanczos3")
