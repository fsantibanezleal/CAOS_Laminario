# U7 · Collection tree, anchors, placement and icons · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: GBIF lineage, the IMA list, Nickel-Strunz in Wikidata, the three BGS RCS volumes, meteorite classes (dossier 09) | (research) | done |
| 2 | The tree in YAML: 191 nodes, EN and ES names and descriptions, rules and priorities, the shared organ systems | R-060 | done |
| 3 | Lock the tree's 134 taxa against the GBIF backbone with their lineages | R-060 | done |
| 4 | Vocabularies: minerals rebuilt from the IMA list and Wikidata; rocks from the RCS volumes with the check; parts, materials, crystals, facets | R-706, R-707 | done |
| 5 | Rules, the tree guard (integrity, reachability, symbolic overlap) and placement by priority | R-060, R-061, R-062 | done |
| 6 | The contract fields (part, preservation, classification), migration 0006, the GBIF taxon cache, the submission check with override and 503 | R-701, R-702, R-705 | done |
| 7 | The API: tree, node, IIIF Collection, facets, anchor search, placement; host views in the slide list | R-703 | done |
| 8 | 186 icons in one sprite, the build (frames, stroke, titles), the gate, the contact sheet reviewed in both themes | R-060, R-704 | done |
| 9 | Wiki page 09 with its diagram (both themes checked), the generated tree reference and its CI check, the collections docs, the GBIF card, design, guide section; version 0.07.000 | (documentation and versioning standards) | done |

## Convergence verdict (2026-09-29, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-060 every node named, described, iconed, ruled; every icon used | `tests/collections/test_tree.py::test_tree_integrity` | pass (Windows and Ubuntu) |
| R-061 overlapping siblings need a priority | `tests/collections/test_tree.py::test_sibling_overlap_needs_priority` | pass (both) |
| R-062 the same suggestion every time, in any sibling order | `tests/collections/test_placement.py::test_deterministic_suggestion` | pass (both) |
| R-701 unresolved anchors and hosts refused, naming the field | `tests/collections/test_api.py::test_submissions_are_checked_against_the_tree` | pass (both) |
| R-702 placement refused outside the accepting nodes, a curator's override accepted | `tests/collections/test_api.py::test_submissions_are_checked_against_the_tree` | pass (both) |
| R-703 IIIF Collections valid against the pinned schema | `tests/collections/test_api.py::test_host_views_and_iiif_collections` | pass (both) |
| R-704 icons inside their frame, one stroke, page colour, titles | `tests/collections/test_icons.py::test_icon_gate` | pass (both) |
| R-705 cached lineage used without the network | `tests/collections/test_taxa.py::test_lineage_is_fetched_once_and_cached` | pass (both) |
| R-706 minerals.json is the rebuild of its sources | `tests/collections/test_vocab.py::test_minerals_json_matches_its_sources` | pass (both, with the vault) |
| R-707 every RCS term occurs in its volume | `tests/collections/test_vocab.py::test_rock_terms_occur_in_their_volumes` | pass (both, with the vault) |

Building it found what the design could not: the GBIF backbone's gaps (no Phthiraptera, Actinopterygii or Reptilia,
F-022), that teaching slides name mineral groups rather than species (F-023), that a rule with exclusions claimed
the higher taxa above it (F-024, fixed by containment), that the standard test payload's host key named another
animal since U1 (F-025), and that the first icon pass met every geometric rule while reading wrongly (F-028). The
web contract test had been failing since U4 without being run (F-030); it is fixed and `npm test` is part of this
verdict.

The full suites ran on the development machine (250 tests, 4 container tests skipped) and on the production host
(with the fixtures, the vocabulary sources, the tusd binary and Docker, deprecation warnings as errors); the web
typecheck, build and tests pass. The counts are in the pull request.

Unmet: none. Owed by later units: the coverage matrix per collection (U8), the tree and icons in the interface (U9,
U10), the live placement in the contribute form (U12), placement after a community identification (U13).
