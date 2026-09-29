# OpenSlide

## What and why

OpenSlide is the vendor-neutral C library that reads whole-slide scanner formats (Aperio SVS, Hamamatsu NDPI and
VMS, 3DHISTECH MRXS, Leica SCN, Philips TIFF, Ventana, DICOM) through one interface: levels, tiles, properties and
the associated images the scanner stored (Goode et al. 2013,
doi:[10.4103/2153-3539.119005](https://doi.org/10.4103/2153-3539.119005)). Laminario reaches it through libvips's
`openslideload`, so scanner files and ordinary images follow one code path.

## Install (exact, verified)

It comes with libvips on both machines: bundled in the Windows `vips-dev-w64-all` build (`libopenslide-1.dll`),
and as `libopenslide0`, a dependency of Ubuntu's `libvips42t64`. No separate Python binding is used.

## Usage

```python
from app.imaging import reader

info = reader.read_info("CMU-1.svs")              # OpenSlide properties through libvips
info.levels, info.mpp_x, info.associated          # 3 levels, 0.499 um/px, ('label', 'macro', 'thumbnail')
label = reader.associated_image(info, "label")    # the real label photograph
```

## Applying it here

- The reader's fixture matrix: CMU-1 (Aperio, 46000 x 32914, 3 levels, 0.499 um/px, label, macro and thumbnail)
  and the Smithsonian ostracod NDPI (3840 x 4608, 7 levels, 0.2289 um/px, macro), equal to their vendor metadata
  (R-010).
- The label and macro photographs give the slide object its real glass (R-201); the NDPI vendor tags place the
  scan on the macro (R-208).

## Caveats and licence

- OpenSlide exposes one focal plane of an NDPI z-stack. The ostracod file holds 71; the reader lists them from the
  Hamamatsu TIFF tags with tifffile and libvips reads each page directly (F-017).
- Associated-image names arrive as one comma-and-space separated property; the reader splits and trims them.
- LGPL-2.1; used as a shared library, unmodified.
