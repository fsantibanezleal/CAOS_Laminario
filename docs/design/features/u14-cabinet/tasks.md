# U14 · The profile cabinet and printable label sheets · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: fourteen label stocks (nine with full layouts from datasheets, templates and die drawings), plain paper with cut lines, iNaturalist's profile and export read from its source (dossier 16) | (research) | done |
| 2 | Label stocks as data, the positions from a start and an offset, the label fitted to any cell, the sheet and the test page | R-1404 to R-1406 | done |
| 3 | Public handles (migration 0012), the profile's counts, the cabinet's slides and identifications, one's own export; accounts named by handle on slides and identifications | R-1401 to R-1403, R-1407 | done |
| 4 | The routes: people, the stocks, the sheet PDF | R-1401 to R-1407 | done |
| 5 | The cabinet place, the print dialog, the account menu's cabinet, the slide's contributor, the identifier's link; stock names and sheet footers in EN and ES; 64 strings | R-080, R-089, R-1408 | done |
| 6 | The cabinet gate in its own sandbox | R-1408, R-080, R-085 | done |
| 7 | Wiki page 16 with its diagram, the U14 design and requirements | (documentation standards) | done |

## Convergence verdict (2026-09-29, on task/37-cabinet before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-080 no sideways scroll at every width, room and language | `frontend/gates/fit.mjs`; `frontend/gates/cabinet.mjs` (the cabinet, its identifications and the print dialog, signed in) | pass: fit 272 cases, 0 failures; the cabinet's 48 fit checks within its 83 |
| R-084 every place reached by pointer | `frontend/gates/walk.mjs`; `frontend/gates/cabinet.mjs` (from a slide to its contributor's cabinet, from an identification to its identifier's, from the account menu to one's own) | pass for the cabinet; the walk's one failure is U10's country list, which waits for U8's bake |
| R-085 no motion under reduced motion | `frontend/gates/motion.mjs`; `frontend/gates/cabinet.mjs` (the cabinet with the print dialog open, both rooms) | pass: 32,919 computed styles, 0 moving; the cabinet's two checks |
| R-089 every string in EN and ES | `frontend/scripts/check-i18n.mjs` | pass: 873 strings in each, 0 problems |
| R-1401 a handle made from the display name, unique; no email | `tests/people/test_profile.py` | pass |
| R-1402 the profile's counts, nothing hidden | `tests/people/test_profile.py` | pass |
| R-1403 the cabinet's slides by collection and its identifications with the community flag | `tests/people/test_profile.py` | pass |
| R-1404 every stock a record; every label on the page and apart | `tests/labels/test_sheet.py::test_every_stock_places_its_labels` | pass |
| R-1405 each label's content inside its label, the quiet zone clear, from the start and the offset | `tests/labels/test_sheet.py` | pass |
| R-1406 the test page's outlines at their size and position within 0.1 mm | `tests/labels/test_sheet.py::test_the_test_page_measures_the_stock` | pass |
| R-1407 one's own slides with exact places; no one else's | `tests/people/test_export.py` | pass |
| R-1408 from a slide to the cabinet, select, print on a stock, the test page | `frontend/gates/cabinet.mjs` | pass: 83 of 83 |

The backend suite on this branch passes except the SDD guard, which names `tests/base/test_base_collection.py`, a
file that exists on U8's branch until it merges (as on U12's and U13's branches). The web typecheck, build and 59
unit tests pass.

Building it found what the design could not: the print dialog and the design spoke of cut marks in the gutters
while the plain-paper PDF draws a dashed line around each label (the words now say what prints, and the sheet's foot
says it in the sheet's language); stock names were English only on the Spanish page; a tray and the slide record
repeated the country when the locality already named it ("Finland, Finlandia"); and the walk's drawer reopened from
a filtered address lost its counts because the facets answered 500 under any modality or licence filter, a U10
defect in the facet query's correlation, fixed here with a test that fails without the fix.
