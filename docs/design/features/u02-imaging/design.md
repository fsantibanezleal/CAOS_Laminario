# U2 · Imaging engine · design

## What the unit delivers

`app/imaging/`, the code that turns an accepted image into what the tile server serves and what the interface
needs, used by the worker (U4) for uploads and by the base-collection scripts (U8):

| Module | Role |
|---|---|
| `library.py` | Loads libvips with OpenSlide through one environment variable (`LAMINARIO_VIPS_BIN`, the folder of the Windows build) or the system library on Linux; exposes what the build supports. |
| `reader.py` | Opens any accepted file: dimensions, level count, pixel size, associated images, and a libvips image of a plane. Refuses oversized images before decoding. |
| `pyramid.py` | Writes one tiled BigTIFF per plane; measures level-0 fidelity; chooses JPEG or WebP per asset. |
| `zstack.py` | The z-plane policy: which planes of a stack are kept, with their original indices and depths. |
| `edf.py` | Extended depth of field: the variance-selection baseline and the complex-wavelet fusion. |
| `derivatives.py` | Thumbnails, the macro crop under the coverslip, the true-scale mount, EXIF-clean output. |
| `guards.py` | The dimension and pixel limits, applied from headers. |

The measurement bench that produced the storage figures lives in `data-pipeline/bench/measure_pyramids.py` and
runs on the fixtures.

## The reader

libvips opens scanner formats through OpenSlide (`openslideload`, one level or one associated image at a time)
and everything else through its own loaders. The reader normalises both into one `SlideInfo`: width and height at
level 0, the level count and downsample factors, the pixel size in micrometres from `openslide.mpp-x` or the TIFF
resolution tags, the vendor, and the names of associated images (`label`, `macro`, `thumbnail`). Alpha is
flattened onto white, because slides are photographed against light.

Before any pixel is decoded, the header dimensions are checked against the limits (200,000 px per side, 20
gigapixels per plane); a refusal is an exception the worker records on the job.

## The pyramid writer

`tiffsave(tile=True, pyramid=True, bigtiff=True, tile_width=512, tile_height=512, compression="jpeg", Q=85)`
gives one file per plane, with levels down to a single tile. The level count is
$L = \lceil \log_2(\max(W, H) / 512) \rceil + 1$, which the test checks by reading the TIFF's page count. When the
pixel size is known it is written into the resolution tags (`xres`, `yres` in pixels per millimetre, unit
centimetre), so any viewer that reads TIFF resolution shows the right scale.

Fidelity is measured, not assumed: 32 regions of 512 x 512 px, positioned by a seeded generator, are read from the
source and from level 0 of the pyramid; the peak signal-to-noise ratio over their pixels is

$$\mathrm{PSNR} = 10 \log_{10} \frac{255^2}{\mathrm{MSE}}, \qquad
\mathrm{MSE} = \frac{1}{N}\sum_i (x_i - y_i)^2 ,$$

and its mean must reach 38 dB, the level at which JPEG at quality 85 is visually transparent for photographic
content. WebP at quality 80 is tried when asked and kept only if its file is smaller than the JPEG file for the
same source, because the research found it larger on dense rock textures.

## The z-plane policy

A stack's full pyramid set is estimated from the plane count times the measured bytes of one plane's pyramid.
When the estimate is at most 500 MB the whole stack is kept. Otherwise $k = 11$ planes are chosen: indices
$\lfloor i (n-1) / (k-1) \rceil$ for $i = 0 \ldots k-1$, which always include both ends and are strictly
increasing when $n \ge k$. Each kept plane records its original index and depth, so the viewer labels real focal
depths.

## Extended depth of field

A z-stack shows each part of a specimen in focus in a different plane. The composite is one image with everything
in focus. Two methods, both implemented, the second the one shipped:

**Variance selection (the baseline).** For each plane, the local variance in a window (here 9 x 9 px) measures
sharpness; each pixel takes the value of the plane with the greatest local variance; the decision map is smoothed
with a Gaussian ($\sigma = 2$ px) so regions do not flicker between planes. Sharpness of the result is measured
with the Tenengrad criterion, the mean squared Sobel gradient magnitude, which must reach 95 % of the sharpest
single plane.

**Complex-wavelet fusion (Forster, Van De Ville, Berent, Sage and Unser, 2004, *Microscopy Research and
Technique* 65:33-42, doi:10.1002/jemt.20092).** Each plane is decomposed with a dual-tree complex wavelet transform
(the near-symmetric 13/19 and Q-shift 14 filters); in every sub-band and at every position the coefficient with the
greatest magnitude across planes is kept, a consistency step makes each position's choice agree with its
neighbours (a majority filter over the plane index), and the inverse transform gives the composite. The
implementation uses PyWavelets for the wavelet transforms (the DTCWT filters ship with it) and NumPy for the
selection. It is accepted only when its structural similarity with the EPFL reference plugin's output on the
reference stacks reaches 0.90 and is not below the baseline's.

The reference outputs are produced once, locally, with the EPFL ImageJ plugin on the reference stacks, and stored
with the fixtures (they are small). The three reference stacks are synthetic and reproducible: a textured sheet
tilted through the focal range, so that every column is sharp in exactly one known plane, at three sizes.

## Derivatives

Thumbnails at 320 and 1024 px on the long side (JPEG Q80), the macro crop under the coverslip (the region of the
slide overview that the coverslip occupies, from the format's geometry), and the true-scale mount: the specimen
image scaled so that its physical width divided by the slide width equals its fraction of the rendered slide
width. Every written derivative goes through libvips with metadata stripped (`strip=True`), so no EXIF, and in
particular no GPS, leaves the server.

## Decisions

- **One library, two builds.** On Windows the official `vips-dev-x64-all` build (it includes OpenSlide); on Ubuntu
  the distribution's `libvips42t64` (built against OpenSlide). `LAMINARIO_VIPS_BIN` names the Windows folder;
  unset on Linux. `pyvips` is installed without its binary extra so it never shadows the chosen library.
- **Fixtures are the research samples.** CMU-1 (Aperio SVS, CC0), the Smithsonian ostracod NDPI (CC BY 4.0), the
  NHM louse scan (TIFF) and the Commons thin section (JPEG), read from `LAMINARIO_FIXTURES` (the local data vault).
  Tests that need a fixture skip with a message when the folder is absent (continuous integration never has
  them), and the convergence verdict records that they ran locally.
- **Pyramids are written to a sandbox in tests**, never to the data root.
