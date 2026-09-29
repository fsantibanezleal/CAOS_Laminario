# U8 · Base collection · requirements

R-070 to R-073 moved here verbatim from the design document. R-801 to R-806 are this unit's own.

```
R-070  THE base collection SHALL hold at least 300 slides, at least 12 per collection and at least 14 whole-slide images.
       Gate: tests/base/test_base_collection.py::test_floors

R-071  EVERY base-collection asset SHALL carry licence, rights holder or creator, source URL, record id, retrieval date and SHA-256, and its licence SHALL be in the base policy set.
       Gate: tests/base/test_base_collection.py::test_asset_provenance

R-072  THE base collection SHALL contain at least one registered PPL/XPL pair per rock family.
       Gate: tests/base/test_base_collection.py::test_polarised_pairs

R-073  THE base-collection bake SHALL write only inside its declared output root, and tests SHALL write only in temporary directories.
       Gate: tests/base/test_bake_sandbox.py::test_tests_never_write_canonical_outputs

R-801  THE picks notation SHALL expand every head form (a sheet number, a polarised pair, an NHM record, a Zenodo file, an OpenSlide file) with its anchor and extras, and SHALL refuse a focal-stack option other than the policy.
       Gate: tests/base/test_picks.py

R-802  EVERY taxon anchor and host of the base collection SHALL have its GBIF record and lineage in data/base/taxa.json, so no later step calls GBIF.
       Gate: tests/base/test_base_collection.py::test_every_taxon_has_its_lineage

R-803  THE validation SHALL check base slides offline with the same contract and tree checks a contribution meets.
       Gate: tests/base/test_base_collection.py::test_a_sample_passes_the_offline_checks

R-804  IF a collection holds fewer than 12 base slides, THEN THE validation SHALL fail unless the collection is recorded with the finding that documents its open supply.
       Gate: tests/base/test_base_collection.py::test_floors

R-805  IF a bake has a failed job, or a stored file differs from its manifest or is missing, THEN THE import SHALL refuse it before writing anything.
       Gate: tests/base/test_importer.py::test_import_refuses_a_tampered_or_failed_bake

R-806  WHEN a bake is imported a second time, THE import SHALL add nothing and skip every slide it already holds.
       Gate: tests/base/test_bake_sandbox.py::test_tests_never_write_canonical_outputs
```

## Status against R-070

R-070 is met for the total (at least 300 slides) and for the whole-slide images (at least 14), and for 17 of the 18
collections. **Reptiles holds 7 slides.** The open, licence-compatible reptile micrographs that pass the acceptance
checks of dossier 06 were searched on Wikimedia Commons (both reptile categories and full-text queries for blood
films, skin, scales, sections and embryos), the Wellcome Collection and GBIF occurrence media; what exists beyond the
seven is multi-panel figures of papers, fossils (which belong to the fossils collection) and non-commercial
licences. The shortfall is recorded as finding F-031 of the planning record and in `SHORTFALLS` in
`app/base/validate.py`; R-804 makes any other shortfall fail. The collection is shown with its seven slides and its
empty sub-collections are open for contribution. R-070 stays open for Reptiles until contributions or a new source
close it.
