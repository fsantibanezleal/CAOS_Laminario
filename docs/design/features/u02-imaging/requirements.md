# U2 · Imaging engine · requirements

R-010 to R-019 moved here from the design document. Three were restated during the unit, each because a
measurement showed the original text could not hold on real data; the original wording, the measurement
and the new wording are recorded under "Restatements" below. R-201 to R-208 are this unit's own.

```
R-010  WHEN a file of any format in the fixture matrix is read, THE reader SHALL return dimensions, level count, pixel size and associated images equal to the vendor metadata.
       Gate: tests/imaging/test_reader.py::test_fixture_matrix_metadata

R-011  THE pyramid writer SHALL produce a tiled BigTIFF with 512 px tiles and ceil(log2(max side / 512)) + 1 levels.
       Gate: tests/imaging/test_pyramid.py::test_level_structure

R-012  THE pyramid writer SHALL reproduce the source at level 0 with mean PSNR of at least 38 dB over 32 seeded 512 px regions, at JPEG Q85, or at JPEG Q90 with full chroma when Q85 falls short.
       Gate: tests/imaging/test_pyramid.py::test_level0_fidelity

R-013  WHEN pixel size is known, THE pyramid writer SHALL write it into the TIFF resolution tags, and WHEN it is not known, SHALL mark the resolution unit as none.
       Gate: tests/imaging/test_pyramid.py::test_resolution_tags

R-014  WHEN a z-stack's full pyramid set exceeds 500 MB, THE processor SHALL keep 11 evenly spaced planes including both ends and record their original indices and depths.
       Gate: tests/imaging/test_zpolicy.py::test_resample_indices_and_depths

R-015  WHEN a z-stack is processed, THE processor SHALL produce a variance-selection composite whose Tenengrad sharpness is at least 0.95 of the sharpest plane on each reference stack.
       Gate: tests/imaging/test_edf.py::test_variance_baseline_sharpness

R-016  WHEN a z-stack is processed, THE processor SHALL produce a wavelet-fusion composite with SSIM of at least 0.90 against the EPFL reference output on each reference stack whose padded size is square, and not lower than the baseline's SSIM against that output.
       Gate: tests/imaging/test_edf.py::test_wavelet_parity_with_reference

R-017  IF an image exceeds 200,000 px on a side or 20 gigapixels in a plane, THEN THE processor SHALL refuse it before decoding pixels.
       Gate: tests/imaging/test_guards.py::test_decompression_bomb_refused

R-018  THE served derivatives SHALL carry no EXIF GPS data.
       Gate: tests/imaging/test_derivatives.py::test_no_gps_in_served_files

R-019  THE true-scale mount SHALL occupy the specimen's physical width divided by the slide width, within 1 percent or half a pixel, whichever is larger.
       Gate: tests/imaging/test_derivatives.py::test_true_scale_mount

R-201  WHEN a scanner file carries a label or macro associated image, THE reader SHALL expose it so the slide can show the real photograph instead of a rendered one.
       Gate: tests/imaging/test_reader.py::test_associated_images_exposed

R-202  WHEN a pyramid is written with WebP tiles, THE writer SHALL keep WebP only if the file is smaller than the JPEG file for the same source and reaches the fidelity floor, else the JPEG file.
       Gate: tests/imaging/test_pyramid.py::test_webp_kept_only_when_smaller

R-203  THE reader SHALL run the same code path on the Windows build of libvips (the official all-in build with OpenSlide) and on Ubuntu's libvips, selecting the library through one environment variable.
       Gate: tests/imaging/test_reader.py::test_library_loads_with_openslide

R-204  WHEN run with the plugin's axis convention, THE fusion SHALL equal the EPFL plugin's height map on at least 99.9 percent of pixels, with composite SSIM of at least 0.999, on every reference stack, for both the wavelet and the variance method.
       Gate: tests/imaging/test_edf.py::test_port_exact_with_plugin_axes

R-205  ON synthetic stacks with known focus, THE wavelet fusion with the true sub-band geometry SHALL be at least as accurate as with the plugin's axis convention, and at least 0.3 more often within one plane of the truth on non-square sizes.
       Gate: tests/imaging/test_edf.py::test_true_geometry_beats_plugin_axes

R-206  THE depth readout SHALL come from the variance height map, which SHALL be within one plane of the known focus on at least 95 percent of pixels of the synthetic stacks, without noise and with noise of standard deviation 3.
       Gate: tests/imaging/test_edf.py::test_depth_readout_from_variance_is_accurate

R-207  WHEN a stack is fused in tiles, THE variance height map SHALL equal the whole-image one, and the wavelet fusion SHALL stay within 0.02 of the whole-image accuracy and within 5 percent of its composite error against known focus.
       Gate: tests/imaging/test_edf.py::test_tiled_matches_whole

R-208  WHEN a scanner file records the slide's size and the scan's position, THE engine SHALL place the scanned region on the macro photograph so that the specimen falls inside it.
       Gate: tests/imaging/test_derivatives.py::test_scan_region_on_macro
```

## Restatements (2026-09-28)

**R-012.** Original: "... mean PSNR of at least 38 dB ... at JPEG Q85." Measured on the fixtures: CMU-1 region
53.6 dB, NHM louse scan 44.0 dB, Commons thin section under crossed polars 32.1 dB. At Q85 libvips subsamples
chroma (4:2:0); the thin section's interference colours are dense chroma detail. At Q90 libvips keeps full
chroma and the same image reaches 49.9 dB (Q88: 32.9 dB, still subsampled). The writer now measures every
plane and rewrites it at Q90 when Q85 falls short: the 38 dB floor holds on every fixture, at 2.9 times the
bytes for that image only.

**R-013.** Extended. Without a known pixel size libvips copied the source's nominal density into the tags
(6400 dpi from the thin section's JPEG header, 96 dpi from the louse scan), which a viewer would show as a
scale. The writer now sets the resolution unit to none in that case.

**R-016.** Original: "... SSIM of at least 0.90 against the EPFL reference output and not lower than the
baseline's." The plugin's consistency checks take the image height as the x extent (``nx = getHeight()`` in
``EdfComplexWavelets.subBandConsistencyCheck`` and ``EdfWaveletMaximumModulus.majCCSubBand``), so on a
non-square padded size they visit regions that are not the sub-bands. With that convention reproduced, the
port equals the plugin on 100 percent of height-map pixels on all three reference stacks (R-204). With the
true geometry, the square case (dome, padded 512 x 512) still equals the plugin (SSIM 1.000), while the
non-square cases differ (eye 0.878, skeleton 0.884) because the reference itself is wrong there: on
synthetic stacks with known focus the plugin's convention is within one plane of the truth on 21 to 27
percent of pixels against 71 to 77 percent for the true geometry, with composite errors of 8.5 to 9.2 grey
levels against 1.0 to 1.8 (R-205). The requirement now applies to the square reference; the non-square
references are covered by R-204 (the port) and R-205 (the accuracy).

**R-019.** Original: "... within 1 percent." A 0.9 mm specimen on a slide drawn 1200 px wide spans 14.4 px;
whole pixels cannot come within 1 percent of that (half a pixel is 3.5 percent). The mount now lands on the
rounded target, and the tolerance is 1 percent or half a pixel, whichever is larger.
