# U13 · Identify · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: iNaturalist's community taxon, quality grade and moderation read from its source; every anchor as a lineage; twelve scenarios (dossier 15) | (research) | done |
| 2 | Every anchor as a lineage; the agreement rule as a pure function; the categories | R-088, R-1302 | done |
| 3 | Migration 0011: identifications, votes, flags, moderation actions; the slide's community node, rank, badge and the status a hidden slide returns to | R-1301, R-1304 to R-1306 | done |
| 4 | The synchronous refresh (community, votes cleared, the slide following, placement and search text, badge); the first identification at publication and at the base import; the backfill command | R-1303, R-1304, R-1309 | done |
| 5 | The API: identify, withdraw, restore, vote, the Identify queue; flags, their resolution, hiding and restoring, the log | R-1301, R-1305 to R-1307 | done |
| 6 | The places: Identify, the slide's identifications, moderation; the masthead's way, the account menu; 124 strings in EN and ES | R-080, R-084, R-089, R-1308 | done |
| 7 | The identify gate on a shared sandbox (the contribute gate moved onto it) | R-1308 | done |
| 8 | Wiki page 15 with its diagram, the U13 design and requirements | (documentation standards) | done |

## Convergence verdict (2026-09-29, on task/36-identify before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-080 no sideways scroll at every width, room and language | `frontend/gates/fit.mjs` (Identify, the populated queue of reference slides); `frontend/gates/identify.mjs` (Identify, moderation and a slide's identifications, signed in as a curator) | pass: fit 272 cases, 0 failures; identify's fit pass within its 60 checks |
| R-084 every place reached by pointer | `frontend/gates/walk.mjs` | pass for the Identify place from the masthead; the walk's one failure is U10's country list, which waits for U8's bake |
| R-085 no motion under reduced motion | `frontend/gates/motion.mjs` | pass: 32,424 computed styles, 0 moving |
| R-088 the deepest node above two thirds | `tests/community/test_agreement.py::test_scenario_table` | pass: the twelve scenarios of dossier 15 |
| R-089 every string in EN and ES | `frontend/scripts/check-i18n.mjs` | pass: 809 strings in each, 0 problems |
| R-1301 one current identification per account, withdrawn and restored | `tests/community/test_identifications.py` | pass |
| R-1302 an ancestor says whether it disagrees | `tests/community/test_agreement.py::test_scenario_table` | pass (scenarios 6 and 7; the API asks with `disagreement_unstated`) |
| R-1303 the slide follows the community; the drawer kept or moved; an override kept | `tests/community/test_follow.py` | pass |
| R-1304 the badge, the vote, the votes cleared | `tests/community/test_quality.py` | pass |
| R-1305 flags and their resolution | `tests/community/test_moderation.py` | pass |
| R-1306 hiding and restoring, gone from every public place, the author told why, the log | `tests/community/test_moderation.py` | pass |
| R-1307 the queue by collection, kind and badge, oldest first | `tests/community/test_queue.py` | pass |
| R-1308 two identifiers agree, verified; hidden; restored | `frontend/gates/identify.mjs` | pass: 60 of 60 |
| R-1309 every published slide carries its first identification | `tests/community/test_identifications.py` | pass (a contribution's and a base slide's; the backfill idempotent) |

The backend suite on this branch: 354 passed, 4 skipped (the IIIF tile tests: the Docker engine was not reachable),
3 failed, the three owed to U8 as on U12's branch (`data/base/acquired.json` and `tests/base/test_base_collection.py`
exist only on U8's branch until it merges). The web typecheck, build and 54 unit tests pass; the contribute gate
passes 206 of 206 on the shared sandbox.

Building it found what the design could not: the slide place kept its record for the page, so after an identification
the record rail said "needs identification" beside a verified agreement (the record is now read again when the badge
or the anchor moves, and the gate checks it without a reload); the rock vocabulary offered its keys as names
("carbonatite"); and the walk gate judged the focus before a lazily loaded place had mounted, because
`networkidle` is already reached after a navigation inside the page.

## Before the release (after merging 0.08.000 to 0.11.000)

The branch that holds U12 to U15 ran every sandbox gate again on 2026-09-29: contribute 206 of 206, identify 60 of 60, cabinet 83 of 83; fit 304 cases and motion 59,019 computed styles with none moving over every place; the backend suite passes: 387 tests, 11 skipped (the ones that start iipsrv in Docker). CI's checks pass locally on this branch (lint, contracts, tokens, contrast, i18n, web unit tests, build, guards).
