# U15 · About the collection · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: attribution practice and the deeds, the NHM Data Portal's citation formats from its source, the base collection's sources and licences from the lock, the vocabularies' citations, the OSM attribution guidelines, the software and fonts with their licences, the links a machine cannot check (dossier 17) | (research) | done |
| 2 | `GET /api/about` and `app/about/credits.json`: the numbers counted when read, sources and licences with their counts, the credits | R-1501, R-1502, R-1507 | done |
| 3 | The About place: the content in EN and ES as typed blocks, the live blocks, five figures in the room's tokens, the equations by KaTeX, the contents beside the text | R-1502, R-1504, R-1507 | done |
| 4 | Cite this slide; the footer on every place; the map's linked credit | R-084, R-1503, R-1506 | done |
| 5 | The About gate, the link check, About in fit, motion and walk | R-080, R-084, R-085, R-1501 to R-1506 | done |
| 6 | Wiki page 17 with its diagram, the U15 design and requirements | (documentation standards) | done |

## Convergence verdict (2026-09-29, on task/38-about before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-080 no sideways scroll at every width, room and language | `frontend/gates/fit.mjs` (every place, About and `/about#licences` included) | pass: 304 cases, 0 failures |
| R-084 every place reached by pointer | `frontend/gates/walk.mjs` (About from the footer); `frontend/gates/about.mjs` | pass for About; the walk's one failure is U10's country list over gate data that predates the countries, which the import of the final bake brings |
| R-085 no motion under reduced motion | `frontend/gates/motion.mjs` | pass: 59,019 computed styles, 0 moving |
| R-089 every string in EN and ES | `frontend/scripts/check-i18n.mjs` | pass: 893 strings in each, 0 problems |
| R-1501 the numbers are the database's | `tests/about/test_about.py`; `frontend/gates/about.mjs` | pass: the counts over published, hidden, base and contributed slides; the page equals the API in both rooms and languages |
| R-1502 every source and licence counted and described | `tests/about/test_about.py`; `frontend/src/about/content.test.ts` | pass: every host of the base lock known, every licence family in the policy, words in both languages |
| R-1503 a slide's citation and each image's attribution | `frontend/src/about/cite.test.ts`; `frontend/gates/about.mjs` | pass: one line per image, TASL with the licence's link and the adaptation, Copy copies what is shown |
| R-1504 the imaging explained with figures and equations | `frontend/src/about/content.test.ts`; `frontend/gates/about.mjs` | pass: five figures in the room's colours, 6 displayed and 11 inline equations typeset, 0 errors |
| R-1505 every external link answers or is listed | `frontend/gates/links.mjs` | pass: 46 links, 43 reachable, 3 not checkable by a machine (Cloudflare challenges at data.nhm.ac.uk and si.edu), 0 broken |
| R-1506 the map links OpenStreetMap's copyright page | `frontend/gates/about.mjs` | pass |
| R-1507 the vocabularies, software and fonts with licences and citations | `frontend/src/about/content.test.ts`; `tests/about/test_about.py` | pass |

The About gate passes 46 of 46. The web typecheck, build and 66 unit tests pass. On this branch, which holds U12 to
U15, the sandbox gates pass again (contribute 206 of 206, identify 60 of 60, cabinet 83 of 83) and the backend suite
passes (387 tests, 11 skipped for Docker); CI's checks pass locally.

Building it found what the design could not: two credit defects of the base collection, fixed in U8 (Commons credits
that carried their file page, one with an email, F-046; OpenSlide scans credited to their host, F-047); the map's
OpenStreetMap credit without its link; and, for the link check, that publishers' DOI landing pages sit behind the same
challenges, so a DOI is checked at doi.org's handle API instead.
