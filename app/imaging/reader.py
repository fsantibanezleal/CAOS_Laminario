"""Open any accepted image file and describe it, before and without decoding its pixels.

Scanner formats (Aperio SVS, Hamamatsu NDPI, and the others OpenSlide reads) are opened through libvips'
OpenSlide loader; everything else (TIFF, JPEG, PNG, WebP) through libvips' own loaders. Both are normalised
into one ``SlideInfo``:

- dimensions and bands at level 0, and the resolution levels the file already carries;
- the pixel size in micrometres, from the vendor (``openslide.mpp-x``), from ImageJ metadata when its unit is
  the micron, or from TIFF resolution tags when their unit is set and the value is in the microscopy range
  (at least 100 px/mm, i.e. at most 10 um/px). Screen defaults such as 72 or 96 dpi are not a calibration
  and are ignored, as is a JPEG's JFIF density;
- the associated images a scanner stores beside the slide (``label``, ``macro``, ``thumbnail``);
- the focal planes: one for a flat image; every level-0 page for a Hamamatsu z-stack, with its depth from
  the ZOffsetFromSlideCentre tag; every page of a multi-page TIFF whose pages share one size (an ImageJ
  stack), with its depth from the ImageJ ``spacing`` when the unit is the micron;
- for Hamamatsu files, the slide's physical size and the scanned region's position on it, from the vendor
  tags, which place the scan on the macro photograph.

The header dimensions are checked against the product's limits before anything else (``guards``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.imaging.guards import check_dimensions
from app.imaging.library import vips

MICROSCOPY_MIN_PX_PER_MM = 100.0
MICRON_UNITS = {"micron", "microns", "um", "µm", "μm"}

# Hamamatsu private TIFF tags (values in nanometres)
NDPI_X_OFFSET = 65422
NDPI_Y_OFFSET = 65423
NDPI_Z_OFFSET = 65424
NDPI_SLIDE_WIDTH = 65496
NDPI_SLIDE_HEIGHT = 65497


@dataclass(frozen=True)
class Level:
    width: int
    height: int
    downsample: float


@dataclass(frozen=True)
class FocalPlane:
    index: int  # position in focal order, 0-based
    page: int | None  # TIFF page holding it at level 0, or None for the file's single image
    depth_um: float | None


@dataclass(frozen=True)
class SlideInfo:
    path: str
    loader: str
    vendor: str | None
    width: int
    height: int
    bands: int
    levels: tuple[Level, ...]
    mpp_x: float | None
    mpp_y: float | None
    mpp_source: str | None  # "vendor", "imagej", "tiff" or None
    objective_power: float | None
    associated: tuple[str, ...]
    planes: tuple[FocalPlane, ...]
    slide_size_mm: tuple[float, float] | None = None
    scan_centre_offset_mm: tuple[float, float] | None = None
    properties: dict = field(default_factory=dict, compare=False, repr=False)

    @property
    def is_stack(self) -> bool:
        return len(self.planes) > 1

    @property
    def megapixels(self) -> float:
        return self.width * self.height / 1e6


def _field(image, name, default=None):
    return image.get(name) if name in image.get_fields() else default


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _openslide_levels(image) -> tuple[Level, ...]:
    count = int(_field(image, "openslide.level-count", 1))
    return tuple(
        Level(
            width=int(image.get(f"openslide.level[{i}].width")),
            height=int(image.get(f"openslide.level[{i}].height")),
            downsample=float(image.get(f"openslide.level[{i}].downsample")),
        )
        for i in range(count)
    )


def _tiff_pages(path: Path):
    import tifffile

    return tifffile.TiffFile(str(path))


def _ndpi_geometry(path: Path, width: int, height: int):
    """Focal planes, slide size and scan offset of a Hamamatsu file, from its private tags."""
    with _tiff_pages(path) as tif:
        level0 = [p for p in tif.pages if p.shape[:2] == (height, width)]
        tags = level0[0].tags
        z = [(p.tags[NDPI_Z_OFFSET].value if NDPI_Z_OFFSET in p.tags else 0, p.index) for p in level0]
        slide = None
        if NDPI_SLIDE_WIDTH in tags and NDPI_SLIDE_HEIGHT in tags:
            slide = (tags[NDPI_SLIDE_WIDTH].value / 1e6, tags[NDPI_SLIDE_HEIGHT].value / 1e6)
        offset = None
        if NDPI_X_OFFSET in tags and NDPI_Y_OFFSET in tags:
            offset = (tags[NDPI_X_OFFSET].value / 1e6, tags[NDPI_Y_OFFSET].value / 1e6)
    ordered = sorted(z)
    if len(ordered) == 1:
        planes = (FocalPlane(0, None, ordered[0][0] / 1000.0),)
    else:
        planes = tuple(FocalPlane(i, page, depth_nm / 1000.0) for i, (depth_nm, page) in enumerate(ordered))
    return planes, slide, offset


def _imagej(path: Path) -> dict | None:
    with _tiff_pages(path) as tif:
        return tif.imagej_metadata


def _tiff_stack_planes(path: Path, pages: int, width: int, height: int) -> tuple[FocalPlane, ...]:
    with _tiff_pages(path) as tif:
        same = [p.index for p in tif.pages if p.shape[:2] == (height, width)]
        meta = tif.imagej_metadata or {}
    if len(same) != pages:
        return (FocalPlane(0, None, None),)  # pages of different sizes: a pyramid or a mix, not a stack
    spacing = _float(meta.get("spacing")) if str(meta.get("unit", "")).lower() in MICRON_UNITS else None
    return tuple(FocalPlane(i, page, i * spacing if spacing else None) for i, page in enumerate(same))


def _tiff_mpp(image, path: Path) -> tuple[float | None, float | None, str | None]:
    meta = _imagej(path) if path.suffix.lower() in (".tif", ".tiff") else None
    if meta and str(meta.get("unit", "")).lower() in MICRON_UNITS:
        import tifffile

        with tifffile.TiffFile(str(path)) as tif:
            tags = tif.pages[0].tags
            if "XResolution" in tags and "YResolution" in tags:
                xn, xd = tags["XResolution"].value
                yn, yd = tags["YResolution"].value
                if xn and yn:
                    return xd / xn, yd / yn, "imagej"
    unit = _field(image, "resolution-unit")
    if unit in ("cm", "in") and image.xres >= MICROSCOPY_MIN_PX_PER_MM and image.yres >= MICROSCOPY_MIN_PX_PER_MM:
        return 1000.0 / image.xres, 1000.0 / image.yres, "tiff"
    return None, None, None


def read_info(path: str | Path) -> SlideInfo:
    """Describe a file from its headers; refuses it (``ImageRefused``) when a limit is broken."""
    path = Path(path)
    image = vips().Image.new_from_file(str(path))
    check_dimensions(image.width, image.height)
    loader = str(_field(image, "vips-loader", "unknown"))
    vendor_prefixes = ("openslide.", "hamamatsu.", "aperio.")
    properties = {k: str(image.get(k)) for k in image.get_fields() if k.startswith(vendor_prefixes)}
    if loader.startswith("openslide"):
        vendor = _field(image, "openslide.vendor")
        mpp_x = _float(_field(image, "openslide.mpp-x"))
        mpp_y = _float(_field(image, "openslide.mpp-y"))
        listed = str(_field(image, "slide-associated-images", "")).split(",")
        associated = tuple(name.strip() for name in listed if name.strip())
        slide_size = offset = None
        planes: tuple[FocalPlane, ...] = (FocalPlane(0, None, None),)
        if vendor == "hamamatsu" and path.suffix.lower() == ".ndpi":
            planes, slide_size, offset = _ndpi_geometry(path, image.width, image.height)
        return SlideInfo(
            path=str(path), loader="openslide", vendor=vendor, width=image.width, height=image.height,
            bands=3, levels=_openslide_levels(image), mpp_x=mpp_x, mpp_y=mpp_y,
            mpp_source="vendor" if mpp_x else None,
            objective_power=_float(_field(image, "openslide.objective-power")), associated=associated,
            planes=planes, slide_size_mm=slide_size, scan_centre_offset_mm=offset, properties=properties,
        )
    pages = int(_field(image, "n-pages", 1) or 1)
    planes = (FocalPlane(0, None, None),)
    mpp_x = mpp_y = source = None
    if loader.startswith("tiff"):
        if pages > 1:
            planes = _tiff_stack_planes(path, pages, image.width, image.height)
        mpp_x, mpp_y, source = _tiff_mpp(image, path)
    bands = image.bands - (1 if image.hasalpha() else 0)
    return SlideInfo(
        path=str(path), loader=loader.removesuffix("_source").removesuffix("load"), vendor=None,
        width=image.width, height=image.height, bands=bands,
        levels=(Level(image.width, image.height, 1.0),), mpp_x=mpp_x, mpp_y=mpp_y, mpp_source=source,
        objective_power=None, associated=(), planes=planes, properties=properties,
    )


def _flatten(image):
    """RGB (or grey) without alpha, transparent areas onto white, 8-bit when the source is 8-bit."""
    if image.hasalpha():
        image = image.flatten(background=[255] * (image.bands - 1))
    if image.format == "double":
        image = image.cast("float")
    elif image.format == "uchar":
        pass
    elif image.format in ("char", "ushort", "short", "uint", "int") and image.interpretation != "rgb16":
        image = image.cast("float") if image.bands == 1 else image.colourspace("srgb")
    elif image.interpretation == "rgb16":
        image = image.colourspace("srgb")
    if image.bands == 4 and image.format == "uchar":
        image = image.extract_band(0, n=3)
    return image


def _ndpi_stream(path: str, page: int):
    """A Hamamatsu plane decoded from its own JPEG stream, for a page libtiff cannot reach.

    NDPI files past 4 GB keep the high bits of their offsets in a private tag, so libtiff reads a wrapped offset and
    stops at the first directory beyond 4 GB ("might cause an IFD loop"). tifffile corrects the offsets and gives the
    plane as its restart-interval chunks; the plane's own JPEG header (full size, restart interval) sits in the file
    just before the first chunk, so the stream from that header to the end of the last chunk is the plane, which
    libvips decodes. For the first planes, which libtiff also reads, both routes give identical pixels.
    """
    import tifffile

    with tifffile.TiffFile(path) as tif:
        tiff_page = tif.pages[page]
        first = tiff_page.dataoffsets[0]
        end = tiff_page.dataoffsets[-1] + tiff_page.databytecounts[-1]
        look = min(first, 65536)
        tif.filehandle.seek(first - look)
        soi = tif.filehandle.read(look).rfind(b"\xff\xd8\xff")
        if soi < 0:
            raise ValueError(f"page {page} of {Path(path).name} has no JPEG header before its data")
        tif.filehandle.seek(first - look + soi)
        stream = tif.filehandle.read(end - (first - look + soi))
    return vips().Image.jpegload_buffer(stream)


def open_plane(info: SlideInfo, plane: int = 0, level: int = 0):
    """A lazy libvips image of one focal plane at one level, alpha flattened onto white."""
    module = vips()
    focal = info.planes[plane]
    if focal.page is not None:
        if level:
            raise ValueError("stack planes are read at level 0; levels come from the written pyramid")
        # A scanner writes a plane as one very large strip, over libtiff's 50 MB allocation guard: the sources here
        # were verified before processing, and the job runs in a killable process with a time limit.
        try:
            image = module.Image.tiffload(info.path, page=focal.page, unlimited=True)
        except module.Error:
            if info.vendor != "hamamatsu":
                raise
            image = _ndpi_stream(info.path, focal.page)
    elif info.loader == "openslide":
        image = module.Image.openslideload(info.path, level=level)
    else:
        if level:
            raise ValueError(f"{Path(info.path).name} has a single level")
        image = module.Image.new_from_file(info.path)
    return _flatten(image)


def associated_image(info: SlideInfo, name: str):
    """A scanner's label, macro or thumbnail photograph, as RGB."""
    if name not in info.associated:
        raise KeyError(f"{Path(info.path).name} has no associated image {name!r}; it has {list(info.associated)}")
    return _flatten(vips().Image.openslideload(info.path, associated=name))


def window(image, x: int, y: int, w: int, h: int) -> np.ndarray:
    """Pixels of a region as an array, (h, w, bands) or (h, w) for one band."""
    region = image.crop(x, y, w, h)
    array = np.ndarray(
        buffer=region.write_to_memory(),
        dtype={"uchar": np.uint8, "float": np.float32, "ushort": np.uint16}[region.format],
        shape=(region.height, region.width, region.bands),
    )
    return array[..., 0] if region.bands == 1 else array
