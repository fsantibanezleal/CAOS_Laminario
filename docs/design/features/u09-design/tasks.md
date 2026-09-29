# U9 · The design system · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: museum and microscopy rooms, faces, hues, motion (dossier 11) | (research) | done |
| 2 | The visual-system spec; tokens in OKLCH for two rooms and 18 collection hues, generated as sRGB | R-081, R-902 | done |
| 3 | The three faces rebuilt from pinned upstream files, the subset renamed | R-901 | done |
| 4 | The room and the language painted from the first frame; typed EN and ES catalogues over Intl | R-089, R-903, R-905 | done |
| 5 | Interface glyphs, the primitives with their states, the specimen place | R-080, R-085, R-904 | done |
| 6 | The fit, motion and states gates; wiki page 11 with its diagram | R-080, R-085, R-904 | done |

## Convergence verdict (2026-09-29, on task/32-design after merging 0.08.000, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-080 no sideways scroll at every width, room and language | `frontend/gates/fit.mjs` | pass: 16 cases, 0 failures |
| R-081 contrast of every text and icon colour | `frontend/scripts/check-contrast.mjs` | pass: 164 pairs, 0 below their minimum |
| R-085 no motion under reduced motion | `frontend/gates/motion.mjs` | pass: 2,514 computed styles, 0 moving |
| R-089 every string in EN and ES | `frontend/scripts/check-i18n.mjs` | pass: 79 strings in each, 0 problems |
| R-901 the fonts equal their rebuild | `scripts/build_fonts.py --check` | pass: 9 files match a rebuild |
| R-902 the token stylesheet equals its rebuild | `frontend/scripts/build-tokens.mjs --check` | pass |
| R-903 a calendar date is the same day everywhere | `frontend/src/i18n/format.test.ts` | pass (7 unit tests) |
| R-904 focus returns to the opener; Escape closes a tooltip | `frontend/gates/states.mjs` | pass: 2 rooms, 0 failures |
| R-905 the room and language from the first frame | `frontend/gates/fit.mjs` | pass |

The web typecheck and build pass. The later interface units run the same gates over every place they add; on the
branch that holds U9 to U15 (task/38-about) fit passes 304 cases and motion 59,019 computed styles with none moving.
