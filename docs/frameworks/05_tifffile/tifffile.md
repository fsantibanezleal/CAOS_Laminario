# tifffile

## What and why

tifffile reads and writes TIFF and its scientific variants (BigTIFF, ImageJ hyperstacks, NDPI, SVS, OME-TIFF) and
exposes every tag, including vendors' private ones. libvips decodes pixels; tifffile reads the metadata libvips
does not surface and edits tags in place.

## Install (exact, verified)

`tifffile==2026.9.20` (in `requirements-api.txt`), pure Python with NumPy.

## Usage

```python
import tifffile

with tifffile.TiffFile("ostracod.ndpi") as tif:
    z_nm = [p.tags[65424].value for p in tif.pages if p.shape[:2] == (4608, 3840)]  # 71 focal depths
    meta = tif.imagej_metadata                                                      # ImageJ stacks
```

## Applying it here

- The reader's NDPI focal planes (tag 65424, z offset in nm), slide size (65496, 65497) and scan position
  (65422, 65423); ImageJ stacks' spacing and unit (`app/imaging/reader.py`).
- The pyramid writer sets the resolution unit to "none" in place when no pixel size is known
  (`TiffTag.overwrite`, `app/imaging/pyramid.py`).
- Tests read the EPFL plugin's reference outputs and write synthetic focal stacks as ImageJ TIFF.

## Caveats and licence

- Hamamatsu tag meanings come from OpenSlide's documentation and were checked on the ostracod file: the box they
  give on the macro photograph holds the specimen (R-208).
- BSD-3-Clause.
