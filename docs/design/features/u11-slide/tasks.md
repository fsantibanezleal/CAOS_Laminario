# U11 · The slide place and the stage · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: the slide as an object, formats, labels and QR, print at 1:1, the stage's optics (dossiers 05 and 13) | (research) | done |
| 2 | One layout in millimetres drawn as SVG and as an A4 PDF at 1:1; the QR | R-083, R-1101 to R-1103 | done |
| 3 | The slide place: the object, the actions, the photographs, the record, every image's provenance; plain images | R-080, R-084, R-1107 | done |
| 4 | The stage: OpenSeadragon over IIIF, objectives and digital zoom, the scale bar, planes, polarisers | R-086, R-1104 to R-1106 | done |
| 5 | Annotations as W3C Web Annotations (migration 0009); `GET /api/session` | R-1108 | done |
| 6 | The QR, scale-bar and stage gates; wiki page 13 with its diagram | R-082, R-086, R-1105, R-1106 | done |

## Convergence verdict (2026-09-29, on task/34-slide after merging 0.10.000, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-080 no sideways scroll | `frontend/gates/fit.mjs` | pass on the branch that holds U9 to U15: 304 cases, 0 failures (the slide and stage places included) |
| R-082 the label's QR decodes to the permalink | `frontend/gates/qr.mjs` | pass: 8 labels, screenshotted at their on-screen size in both rooms at two widths, decoded to their permalink |
| R-083 the print measures the format within 0.1 mm | `tests/labels/test_print.py::test_print_dimensions` | pass |
| R-084 every place by pointer | `frontend/gates/walk.mjs` | pass for the slide and its stage (13 steps; the one failure is U10's country list over gate data that predates the countries) |
| R-085 no motion under reduced motion | `frontend/gates/motion.mjs` | pass on the branch that holds U9 to U15: 59,019 computed styles, 0 moving |
| R-086 the scale bar within 1 percent at every objective | `frontend/gates/scalebar.mjs` | runs against the live site (U16): the tile server runs on the host |
| R-089 every string in EN and ES | `frontend/scripts/check-i18n.mjs` | pass: 275 strings in each, 0 problems |
| R-1101 one layout for screen and print | `tests/labels/test_layout.py` | pass |
| R-1102 the label's contents, the quiet zone clear | `tests/labels/test_layout.py::test_quiet_zone_and_contents` | pass |
| R-1103 the QR alphanumeric, the same in SVG and PDF | `tests/labels/test_qr.py` | pass |
| R-1104 objectives, digital zoom, not to scale | `frontend/src/stage/optics.test.ts` | pass (25 web unit tests) |
| R-1105 planes aligned and named by depth | `frontend/gates/stage.mjs` | runs against the live site (U16) |
| R-1106 the polarised pair on one field, rotation in degrees | `frontend/gates/stage.mjs` | runs against the live site (U16) |
| R-1107 every image's provenance on the slide place | `frontend/gates/walk.mjs` | pass on the same run |
| R-1108 annotations stored, authored and removed by their roles | `tests/annotations/test_annotations.py` | pass |

The scale-bar and stage gates need tiles from iipsrv, which runs only from its pinned container; the workstation's
Docker engine is unavailable, and the host runs it. U16's production gates run them against the live site, over the
base collection's own scans and stacks, and U16's verdict records the result.

The backend suite on this branch: 315 passed, 9 skipped (the tests that start iipsrv in Docker). CI's checks pass
locally (lint, contracts, tokens, contrast 178 pairs, i18n, 25 web unit tests, build, guards).
