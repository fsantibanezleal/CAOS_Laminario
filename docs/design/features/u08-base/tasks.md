# U8 · The base collection · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: open slide collections and their licences, availability per collection (dossiers 01, 06, 10) | (research) | done |
| 2 | The lane: harvest, picks, lock, acquisition, validation, bake, import | R-073, R-801, R-803, R-805, R-806 | done |
| 3 | The picks over 18 collections and 14 whole-slide scans; the lock with GBIF names and lineages | R-070, R-071, R-072, R-802 | done |
| 4 | Acquisition of every image into the vault with its SHA-256 | R-071 | done |
| 5 | The validation report and the coverage per collection and sub-collection | R-070, R-803, R-804 | done |
| 6 | The bake through the product's pipeline and its import, sandboxed in the tests | R-073, R-805, R-806 | done |
| 7 | Wiki page 10 with its diagram, the operator guide, the U8 design and requirements | (documentation standards) | done |

## Convergence verdict (2026-09-29, on task/31-base before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-070 at least 300 slides, 12 per collection, 14 whole-slide images | `tests/base/test_base_collection.py::test_floors`; `python -m app.base validate` | pass: 505 slides, 14 whole-slide images, 17 of 18 collections at 12 or more; Reptiles at 7 with its recorded supply (F-031), as R-804 allows |
| R-071 every asset's licence and provenance | `tests/base/test_base_collection.py::test_asset_provenance` | pass: 537 images, every licence in the base policy |
| R-072 a polarised pair per rock family | `tests/base/test_base_collection.py::test_polarised_pairs` | pass: igneous, metamorphic, sedimentary |
| R-073 the bake writes only in its root; tests only in temporary folders | `tests/base/test_bake_sandbox.py` | pass |
| R-801 the picks notation | `tests/base/test_picks.py` | pass |
| R-802 every taxon's lineage recorded | `tests/base/test_base_collection.py::test_every_taxon_has_its_lineage` | pass (a kingdom's empty lineage is its whole path) |
| R-803 validation offline with a contribution's checks | `tests/base/test_base_collection.py::test_a_sample_passes_the_offline_checks`; `python -m app.base validate` | pass: 0 of 505 slides failing a check |
| R-804 a collection below 12 fails unless recorded | `tests/base/test_base_collection.py::test_floors` | pass |
| R-805 a failed or tampered bake refused | `tests/base/test_importer.py` | pass |
| R-806 a second import adds nothing | `tests/base/test_bake_sandbox.py` | pass |

The full bake of the 505 slides into the production data root runs on the workstation through the worker (focal
stacks of the NMNH take hours each) and is imported on the host by U16; the bake of every slide the lock held before
the last changes succeeded, and its failures were the two samples replaced here.

Building it found what the design could not: two OpenSlide samples the product itself cannot read (F-043, F-045),
Commons credits that carried their file page with them, one with an email address (F-046), OpenSlide scans credited
to their host rather than their authors (F-047), a worker job that opened the repository's default database instead
of the bake's, and NDPI planes refused by libtiff's allocation guard.
