# U17 · The glass-slide interface · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: the slide and coverslip standards, how slides are kept (cabinets, boxes, folders), which base slides can be real glass, rendering glass in the browser, the carousel pattern (dossier 18) | (research) | done |
| 2 | The scanner's macro photograph stored as the slide's overview (`extract_overview`), queued after a scan and by the bake; `glass_photo_url` in the summary | R-1707, R-1703 | done |
| 3 | The model: the object's dimensions, the arrangements' layouts, the keys; tested | R-1703, R-1704, R-1705 | done |
| 4 | The scene: glass, labels, coverslip, photographs, cabinet drawer, slide box, folder, shadows, camera, the slides' places on the stage | R-1701, R-1703, R-1706 | done |
| 5 | The set in the page: arrangement choice kept, the stage, the caption, the accessible layer, the flat drawing | R-1701, R-1704, R-1705, R-1708 | done |
| 6 | Every place converted: the landing, a collection, a drawer, search, Identify, the map's preview, the profile; every box a glass plate | R-1701, R-1702 | done |
| 7 | The glass gate, the screenshots, the walk through the scene, R-1007 on the flat drawing; every gate with software WebGL | R-1701 to R-1708, R-1007 | written; not run for this release (below) |
| 8 | Wiki page 19 with its diagram, the explore page brought up to date, the U17 design and requirements | (documentation standards) | done |

## Verdict (2026-09-30, before the release)

| Check | Result |
|---|---|
| The web app's typecheck and build | pass; the 3D code is its own chunk (1,003 KB, 271 KB compressed) beside the 350 KB of the app |
| `frontend/src/glass/model.test.ts`, `items.test.ts` and the app's other unit tests | pass: 81 tests (R-1703 and the layouts) |
| `tests/worker/test_processing.py` and the backend suite | pass: 400 tests, 11 skipped (R-1707 on the CMU-1 scan) |
| CI's checks run locally (ruff, contracts, tree docs, hygiene, content standards, SDD, tokens, contrast, i18n 908 strings in each language) | pass |
| `frontend/gates/production.mjs` against the live site, which runs this branch | pass: 22 of 22 |
| `frontend/gates/glass.mjs`, `walk.mjs`, `fit.mjs`, `motion.mjs`, `qr.mjs` (the browser gates) | not run for this release, on Felipe's instruction ("skip the browser use"); the first screenshots of the landing's carousel and of a collection's drawer, box and folder were read and led to the fixes recorded in the design (the glass over the page's surface, the icon as a cut-out, the shadows, the drawer's pitch and lift) |

The interface was installed on the live site from this branch before its release, on Felipe's instruction, and serves the
base collection.

