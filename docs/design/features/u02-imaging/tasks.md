# U2 · Imaging engine · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Library loading through `LAMINARIO_VIPS_BIN` (environment or `.env`), build report | R-203 | done |
| 2 | Reader: headers, levels, pixel size with its source, associated images, focal planes (NDPI tags, ImageJ stacks), slide geometry; pixels by plane and window | R-010, R-201 | done |
| 3 | Limits from headers before decoding | R-017 | done |
| 4 | Pyramid writer: BigTIFF, 512 px tiles, measured PSNR, Q90 full-chroma fallback, WebP rule, resolution tags or unit none | R-011, R-012, R-013, R-202 | done |
| 5 | Z-plane policy | R-014 | done |
| 6 | Complex wavelet transform ported from the plugin, checked against its Java on four configurations | R-204 | done |
| 7 | EDF: variance selection and complex wavelet fusion with the plugin's conventions, then the true sub-band geometry; tiles; colour composite; depth map | R-015, R-016, R-204, R-205, R-206, R-207 | done |
| 8 | Derivatives: thumbnails, clean saving (ICC only), scan on the macro photograph, crop under the coverslip, true-scale mount | R-018, R-019, R-208, R-209 | done |
| 9 | Synthetic focal stacks with known focus; `scripts/bench_imaging.py` reproducing every table of the wiki page | (measurement) | done |
| 10 | Fixtures in the data vault (`samples/`, `edf-reference/` with the plugin runners), prerequisites check, guide section | (local run standard) | done |
| 11 | Wiki page 04 with the pipeline diagram (checked in both themes); design; restatements; version 0.02.000 | (documentation and versioning standards) | done |

## Convergence verdict (2026-09-28, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-010 reader equals vendor metadata | `tests/imaging/test_reader.py::test_fixture_matrix_metadata` (4 formats) | pass |
| R-011 level structure | `tests/imaging/test_pyramid.py::test_level_structure` | pass |
| R-012 level-0 PSNR at least 38 dB | `tests/imaging/test_pyramid.py::test_level0_fidelity` (3 content types; thin section through the fallback) | pass |
| R-013 resolution tags | `tests/imaging/test_pyramid.py::test_resolution_tags` | pass |
| R-014 z-plane policy | `tests/imaging/test_zpolicy.py::test_resample_indices_and_depths` | pass |
| R-015 variance sharpness | `tests/imaging/test_edf.py::test_variance_baseline_sharpness` (3 stacks) | pass |
| R-016 wavelet parity on the square reference | `tests/imaging/test_edf.py::test_wavelet_parity_with_reference` | pass |
| R-017 bombs refused before decoding | `tests/imaging/test_guards.py::test_decompression_bomb_refused` (3 headers) | pass |
| R-018 no GPS in derivatives | `tests/imaging/test_derivatives.py::test_no_gps_in_served_files` | pass |
| R-019 true-scale mount | `tests/imaging/test_derivatives.py::test_true_scale_mount` (3 sizes) | pass |
| R-201 associated images | `tests/imaging/test_reader.py::test_associated_images_exposed` | pass |
| R-202 WebP only when smaller | `tests/imaging/test_pyramid.py::test_webp_kept_only_when_smaller` (both outcomes) | pass |
| R-203 library with OpenSlide | `tests/imaging/test_reader.py::test_library_loads_with_openslide` | pass (Windows build 8.18.6); the Ubuntu build is checked at U16 |
| R-204 exact port | `tests/imaging/test_edf.py::test_port_exact_with_plugin_axes` (3 stacks x 2 methods) | pass, 100 percent |
| R-205 true geometry more accurate | `tests/imaging/test_edf.py::test_true_geometry_beats_plugin_axes` | pass |
| R-206 depth readout accuracy | `tests/imaging/test_edf.py::test_depth_readout_from_variance_is_accurate` | pass |
| R-207 tiles | `tests/imaging/test_edf.py::test_tiled_matches_whole` | pass |
| R-208 scan on the macro photograph | `tests/imaging/test_derivatives.py::test_scan_region_on_macro` | pass |
| R-209 crop under the coverslip | `tests/imaging/test_derivatives.py::test_coverslip_crop` (2 sizes x 2 orientations) | pass |

Also run: the full `pytest` suite with the fixtures (the count is in the pull request); `ruff` clean; the five
guards pass; `export_contracts.py --check` OK; the bench reproduces the wiki's tables; the pipeline diagram
rendered headless in both colour schemes and inspected.

Unmet: none. Open for later units: R-203 on Ubuntu (U16, on the ml box); iipsrv reading WebP-compressed TIFF
tiles (U3).
