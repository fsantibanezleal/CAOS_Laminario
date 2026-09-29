# U2 · Imaging engine · design

The theory, the equations and every measurement are in the wiki page
[04 The imaging engine](../../../architecture/04_imaging.md); this page records the unit's decisions.

## What the unit delivers

`app/imaging/`, used by the worker (U4) for uploads and by the base-collection scripts (U8):

| Module | Role |
|---|---|
| `library.py` | Loads libvips with OpenSlide through `LAMINARIO_VIPS_BIN` (the Windows build's folder, from the environment or `.env`) or the system library on Linux; reports whether the build reads scanner formats. |
| `reader.py` | `read_info` describes a file from headers (levels, pixel size and its source, objective, associated images, focal planes with depths, slide geometry); `open_plane`, `associated_image` and `window` give pixels. |
| `guards.py` | Side and plane limits, applied by `read_info` before any decoding. |
| `pyramid.py` | `write_pyramid`: one BigTIFF per plane with measured level-0 fidelity, the quality fallback, the WebP rule and the resolution tags. |
| `zstack.py` | The plane policy. |
| `complex_wavelet.py` | The plugin's complex wavelet transform. |
| `edf.py` | `fuse` (any size, through a window reader) and `fuse_array`: variance selection and complex wavelet fusion, both with the plugin's conventions available (`plugin_axes`). |
| `derivatives.py` | Thumbnails, clean saving, the scan on the macro photograph, the true-scale mount. |

## Decisions

- **Port the reference, then prove it.** The EDF methods follow the EPFL plugin line by line (read from its
  source), including its single-precision arithmetic, its summation order and its tie rules, so the port can
  be proven exact against the plugin's own output (100 percent of height-map pixels on the three reference
  stacks). A green SSIM threshold alone would not show that the method is the published one.
- **Correct the reference where it is measurably wrong.** The plugin's consistency checks swap width and
  height; on non-square sizes that makes its height maps three times less often right on stacks with known
  focus. The true geometry is the default; the plugin's is an option used by the port proof.
- **Two EDF outputs per stack.** The variance height map is the depth readout (0.93 to 0.999 within one plane
  of the truth, against 0.29 to 0.77 for the wavelet map); the wavelet composite is the default image, as the
  design document states, with the variance composite available.
- **EDF reads the written planes.** For large stacks the worker writes each plane's pyramid first (needed for
  the z viewer anyway) and fuses from those files in 1024 px windows with 128 px margins, so memory is bounded
  by one window of all planes. For a 71-plane stack that is 71 x 1024 x 1024 x 3 bytes of pixels plus the
  coefficient stack for the window (kept in memory up to 512 MB, recomputed plane by plane above that).
- **Measure fidelity per plane.** JPEG Q85 by default; a plane that falls below 38 dB is rewritten at Q90,
  where libvips keeps full chroma. Measured necessary on crossed-polar thin sections (32.1 dB at Q85).
- **No fake scale.** Resolution tags carry the pixel size only when a trustworthy source gives it; otherwise
  the resolution unit is none.
- **One library, two builds.** On Windows the official `vips-dev-x64-all` build (it includes OpenSlide); on
  Ubuntu the distribution's `libvips42t64`. `pyvips` is installed without its binary extra.
- **Fixtures stay out of git.** `LAMINARIO_FIXTURES` names the local data vault: `samples/` (CMU-1, the
  ostracod NDPI, the NHM louse scan and label, the Commons thin section) and `edf-reference/` (the plugin's
  three sample stacks, its outputs for the "high" and "low-medium" presets, the transform dumps, and the two
  Java runners that produced them). Tests that need them skip without it; continuous integration never has
  them.
- **Tests write to a sandbox** (`LAMINARIO_TEST_TMP`, on the scratch drive), never to the data root.

## Interfaces used by later units

- U3 (IIIF): the BigTIFF files `write_pyramid` writes are what iipsrv serves; WebP-compressed TIFF tiles need
  libtiff with WebP on the server (to verify at U3).
- U4 (worker): `read_info`, `select_planes`, `write_pyramid`, `fuse` with its `progress` callback, and the
  derivatives, each a step of the processing job.
- U8 (base collection): the same calls from the import scripts; `scan_region_on_macro` places NDPI scans on
  their macro photographs.
- U11 (slide object): the associated label and macro images, the scan box, the true-scale mount, the depth map.
