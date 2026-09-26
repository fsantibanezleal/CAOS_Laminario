# U2 · Imaging engine · requirements

R-010 to R-019 moved here verbatim from the design document. R-201 to R-203 are this unit's own.

```
R-010  WHEN a file of any format in the fixture matrix is read, THE reader SHALL return dimensions, level count, pixel size and associated images equal to the vendor metadata.
       Gate: tests/imaging/test_reader.py::test_fixture_matrix_metadata

R-011  THE pyramid writer SHALL produce a tiled BigTIFF with 512 px tiles and ceil(log2(max side / 512)) + 1 levels.
       Gate: tests/imaging/test_pyramid.py::test_level_structure

R-012  THE pyramid writer SHALL reproduce the source at level 0 with mean PSNR of at least 38 dB over 32 seeded 512 px regions at JPEG Q85.
       Gate: tests/imaging/test_pyramid.py::test_level0_fidelity

R-013  WHEN pixel size is known, THE pyramid writer SHALL write it into the TIFF resolution tags.
       Gate: tests/imaging/test_pyramid.py::test_resolution_tags

R-014  WHEN a z-stack's full pyramid set exceeds 500 MB, THE processor SHALL keep 11 evenly spaced planes including both ends and record their original indices and depths.
       Gate: tests/imaging/test_zpolicy.py::test_resample_indices_and_depths

R-015  WHEN a z-stack is processed, THE processor SHALL produce a variance-selection composite whose Tenengrad sharpness is at least 0.95 of the sharpest plane on each reference stack.
       Gate: tests/imaging/test_edf.py::test_variance_baseline_sharpness

R-016  WHEN a z-stack is processed, THE processor SHALL produce a wavelet-fusion composite with SSIM of at least 0.90 against the EPFL reference output and not lower than the baseline's.
       Gate: tests/imaging/test_edf.py::test_wavelet_parity_with_reference

R-017  IF an image exceeds 200,000 px on a side or 20 gigapixels in a plane, THEN THE processor SHALL refuse it before decoding pixels.
       Gate: tests/imaging/test_guards.py::test_decompression_bomb_refused

R-018  THE served derivatives SHALL carry no EXIF GPS data.
       Gate: tests/imaging/test_derivatives.py::test_no_gps_in_served_files

R-019  THE true-scale mount SHALL occupy the specimen's physical width divided by the slide width, within 1 percent.
       Gate: tests/imaging/test_derivatives.py::test_true_scale_mount

R-201  WHEN a scanner file carries a label or macro associated image, THE reader SHALL expose it so the slide can show the real photograph instead of a rendered one.
       Gate: tests/imaging/test_reader.py::test_associated_images_exposed

R-202  WHEN a pyramid is written with WebP tiles, THE writer SHALL keep WebP only if the file is smaller than the JPEG Q85 file for the same source, else the JPEG file.
       Gate: tests/imaging/test_pyramid.py::test_webp_kept_only_when_smaller

R-203  THE reader SHALL run the same code path on the Windows build of libvips (the official all-in build with OpenSlide) and on Ubuntu's libvips, selecting the library through one environment variable.
       Gate: tests/imaging/test_reader.py::test_library_loads_with_openslide
```
