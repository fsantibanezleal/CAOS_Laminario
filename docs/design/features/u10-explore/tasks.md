# U10 · Explore · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: the places, addresses and focus, search, facets, countries, the map and its basemap (dossier 12) | (research) | done |
| 2 | A slide's country (stated or implied), FTS5 search over a composed text, faceted counts, the map after geoprivacy (migration 0008) | R-1001 to R-1004 | done |
| 3 | The country vocabulary and shapes rebuilt from pinned sources; the basemap as a verified extract served with byte ranges | R-1005, R-1008 | done |
| 4 | The places: realms, cabinets, drawers with their tray, filters in the address, search, the map; focus and scroll on navigation | R-080, R-084, R-085, R-1006, R-1007 | done |
| 5 | Base slides placed in the countries their sources state; record-only refreshes of the bake and the import | R-1009 | done |
| 6 | The walk gate; wiki page 12 with its diagram | R-084, R-1006, R-1007 | done |

## Convergence verdict (2026-09-29, on task/33-explore after merging 0.09.000, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-080 no sideways scroll at every width, room and language | `frontend/gates/fit.mjs` | pass: 144 cases, 0 failures |
| R-084 every place reached by pointer | `frontend/gates/walk.mjs` | pass for every place of the unit (10 steps); the one failure is the map's country list: the gate data was imported from a bake made before R-1009's countries, and the final bake's record refresh brings them (checked on the live site by U16) |
| R-085 no motion under reduced motion | `frontend/gates/motion.mjs` | pass: 22,176 computed styles, 0 moving |
| R-089 every string in EN and ES | `frontend/scripts/check-i18n.mjs` | pass: 179 strings in each, 0 problems |
| R-1001 filters and faceted counts | `tests/explore/test_explore.py::test_filters_and_facet_counts` | pass |
| R-1002 search in both languages, prefixes, catalogue numbers, never as syntax | `tests/explore/test_explore.py::test_search` | pass |
| R-1003 the map after geoprivacy | `tests/explore/test_explore.py::test_map_after_geoprivacy` | pass |
| R-1004 a stated country checked against the point | `tests/collections/test_places.py` | pass |
| R-1005 the countries and the basemap equal their pinned sources | `scripts/build_countries.py --check`; the extract's SHA-256 | pass: the vocabulary and shapes match a rebuild; the extract's SHA-256 equals the recorded 7d21f20a... |
| R-1006 an address reopens the same place; focus on the heading | `frontend/gates/walk.mjs` | pass |
| R-1007 the tray at the formats' proportion, one scale | `frontend/gates/walk.mjs` | pass: 17 slides measured |
| R-1008 the basemap by byte ranges; the map without it | `tests/explore/test_basemap.py` | pass |
| R-1009 countries only where stated; record changes without reprocessing | `tests/base/test_countries.py` | pass |

The states gate passes in both rooms. The backend suite on this branch passes: 290 tests, the four IIIF tile tests skipped (they start iipsrv in Docker, which the workstation cannot run). The web typecheck and build pass.

Thumbnails on the tray need the tile server, which runs on the host: they are checked on the live site (U16).
