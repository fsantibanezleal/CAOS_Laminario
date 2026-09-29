# U12 · Contribute · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: the API's gaps, Uppy and exifr measured, where GPS lives in each accepted format, pixel-size calibration, the lifecycle (dossier 14) | (research) | done |
| 2 | A code and parameters on every validation error and flag; the interface's words for each code in EN and ES | R-1202 | done |
| 3 | The case lifecycle: submit, publication when processed, back to draft with the reason; the contributor's drafts listed, reopened, changed, deleted (migration 0010) | R-1205, R-1206 | done |
| 4 | A private case's file refused while it carries a GPS position | R-1203 | done |
| 5 | The location routine for JPEG, PNG, WebP and TIFF; the photo reader | R-1204, R-087 | done |
| 6 | Pixel-size calibration on a stage micrometer, with its uncertainty | R-1207 | done |
| 7 | The account places and the masthead's account; registration refusals with codes | R-1201 | done |
| 8 | The contribute places: the list, the case editor in six sections with the slide drawn to scale, the anchor combobox, the parts vocabulary (`GET /api/vocab/parts`), the point map, geoprivacy, the drawer, uploads with Uppy over tus, verification and processing followed by their events | R-087, R-1201, R-1208 | done |
| 9 | Each image keeps its original's SHA-256, shown on its slide | R-1208 | done |
| 10 | The end-to-end gate in its own sandbox; the account places in the shared gates | R-080, R-084, R-085, R-087, R-1201, R-1208 | done |
| 11 | Wiki page 14 with its diagram, the guide (the vault photograph, the gate), the U12 design and requirements | (documentation standards) | done |

## Convergence verdict (2026-09-29, on task/35-contribute before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-080 no sideways scroll at 360, 768, 1280 and 1920 px, both rooms and languages | `frontend/gates/fit.mjs` (account places); `frontend/gates/contribute.mjs` (the list and every section of the editor, signed in) | pass: fit 240 cases, 0 failures; contribute's fit pass included in its 206 checks |
| R-084 every place reached by pointer | `frontend/gates/walk.mjs` | pass for U12's steps (the masthead's sign-in, the reset link, a visitor sent from /contribute to sign in); the walk's one failure is U10's country list, which waits for U8's bake |
| R-085 no motion under reduced motion | `frontend/gates/motion.mjs` | pass: 27,471 computed styles, 0 moving |
| R-087 a photograph's position shown before upload, removed when private | `frontend/gates/contribute.mjs` | pass: shown, then absent from the stored file with its date kept |
| R-089 every string in EN and ES | `frontend/scripts/check-i18n.mjs` | pass: 685 strings in each, 0 problems |
| R-1201 sign in, join, reset, sign out; the masthead names the account | `frontend/gates/contribute.mjs` | pass: joined from a command-line invitation, signed out, a wrong password refused in words, signed in again |
| R-1202 codes and parameters on every message | `tests/contracts/test_error_codes.py`; `frontend/src/contribute/messages.test.ts` | pass |
| R-1203 a private case's file with a position refused | `tests/uploads/test_location.py` | pass |
| R-1204 position and XMP removed, image, date and orientation kept | `frontend/src/contribute/location.test.ts` | pass (JPEG, PNG, WebP, TIFF, read back with exifr) |
| R-1205 draft, processing, published, back to draft with the reason | `tests/contribute/test_lifecycle.py` | pass |
| R-1206 own drafts only | `tests/contribute/test_lifecycle.py` | pass |
| R-1207 d / n and 2p / n | `frontend/src/contribute/calibration.test.ts` | pass |
| R-1208 CMU-1 and a photograph through tus, verified, processed, published, opened with the file's SHA-256 | `frontend/gates/contribute.mjs` | pass: 206 of 206 checks |

The backend suite on this branch: 314 passed, 4 skipped (the IIIF tile tests: the Docker engine was not reachable on
this machine), 3 failed. The three failures belong to U8 and are not U12's: `data/base/acquired.json` and
`tests/base/test_base_collection.py` exist only on U8's branch until it merges, so two base tests and the SDD guard
(which checks that every requirement's gate exists) fail on any branch cut from develop before then. The web
typecheck, build and 54 unit tests pass.

Building it found what the design could not: Vite's proxy turned a string target into `changeOrigin: true`, so tusd
gave the browser upload addresses on its own port (F-044); the editor's side column widened to the rail's width at
360 px, and example values shown as placeholders read as filled-in values in the lamp-lit room (both fixed and gated).

## Before the release (after merging 0.08.000 to 0.11.000)

The branch that holds U12 to U15 ran every sandbox gate again on 2026-09-29: contribute 206 of 206, identify 60 of 60, cabinet 83 of 83; fit 304 cases and motion 59,019 computed styles with none moving over every place; the backend suite passes: 387 tests, 11 skipped (the ones that start iipsrv in Docker). CI's checks pass locally on this branch (lint, contracts, tokens, contrast, i18n, web unit tests, build, guards).
