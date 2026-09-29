# libvips, through pyvips

## What and why

libvips is a demand-driven, horizontally threaded image processing library: it streams an image through a
pipeline in small regions instead of loading it, so a 1.5-gigapixel slide is read, converted and written as a
pyramid in about 30 s of CPU with modest memory (Martinez and Cupitt 2005,
doi:[10.1109/ICIP.2005.1530120](https://doi.org/10.1109/ICIP.2005.1530120)). It reads every format Laminario
accepts (through OpenSlide for scanner files, its own loaders for TIFF, JPEG, PNG, WebP) and writes tiled
pyramidal BigTIFF in one call. The storage research compared it with static IIIF tile trees and DeepZoom and
measured one BigTIFF per plane at the same bytes as 7,879 tile files for CMU-1 (dossier 04).

## Install (exact, verified)

| Machine | Build | Version |
|---|---|---|
| Windows (development) | the official `vips-dev-w64-all` build, which bundles OpenSlide, unzipped anywhere; `LAMINARIO_VIPS_BIN` in `.env` names its `bin` folder | 8.18.6 |
| Ubuntu 24.04 (production) | `apt install libvips42t64 libvips-tools` (built against OpenSlide) | 8.15.1 |
| Python binding | `pyvips==3.2.0` (cffi ABI mode), installed without its binary extra so it never shadows the chosen library | 3.2.0 |

The engine needs at least 8.15 (the `keep=` option that controls which metadata a writer copies);
`tests/imaging/test_reader.py::test_library_loads_with_openslide` checks both the version and the OpenSlide
loader.

## Usage

```python
from app.imaging.library import vips

pyvips = vips()                                   # locates the library once
image = pyvips.Image.new_from_file("scan.tif")     # lazy: only the header is read
image.tiffsave("plane.tif", tile=True, pyramid=True, bigtiff=True, tile_width=512, tile_height=512,
               compression="jpeg", Q=85, keep="icc")
```

## Applying it here

- `app/imaging/reader.py`: headers, levels, pixel size, associated images, windows of pixels.
- `app/imaging/pyramid.py`: the pyramid writer, with its measured fidelity ladder (Q85, Q90 full chroma, Q95).
- `app/imaging/derivatives.py`: thumbnails and clean saves (`keep="icc"`: no EXIF, no GPS).
- `app/jobs/kinds.py`: every processing job goes through these modules.

## Caveats and licence

- Below quality 90, libvips subsamples chroma (4:2:0) when writing JPEG; that cost 17 dB on a crossed-polar thin
  section (F-016), hence the ladder.
- Without a pixel size, `tiffsave` copies the source's nominal density into the resolution tags; the writer
  overwrites the unit with "none" (R-013).
- libvips caches operations, which keeps files open; on Windows an open file cannot be replaced or deleted, so the
  writer releases the cache (`cache_set_max(0)`) after measuring a file.
- LGPL-2.1-or-later; used as a shared library, unmodified.
