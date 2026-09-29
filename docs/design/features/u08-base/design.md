# U8 · Base collection · design

The lane, with its diagram, is in the wiki page [10 The base collection](../../../architecture/10_base-collection.md);
the operator's sequence is in the guide [02 Build the base collection](../../../guides/02_base-collection.md); the
composition is in [base-report.md](../../../collections/base-report.md) and [coverage.md](../../../collections/coverage.md).
The research is dossiers 01, 04 and 06, re-verified in dossier 10, of the planning record. This page records the
unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| The source adapters: Commons categories and named files, NHM imaged records (slide photograph as macro, scan as micro, taxon from the GBIF occurrence), Smithsonian Open Access (CC0 media), Zenodo records with MD5, the OpenSlide index with SHA-256 | `app/base/sources/`, `app/base/lock.py` (`_wsi`) |
| The harvest with numbered review sheets | `app/base/__main__.py` (`harvest`), `app/base/review.py`, `data/base/harvest.yaml` |
| The picks notation and the selection | `app/base/picks.py`, `data/base/picks/*.txt`, `data/base/selection.yaml` |
| The lock: strict GBIF names, lineages, placement by the tree | `app/base/lock.py`, `app/base/names.py`, `data/base/{lock.yaml,names.json,taxa.json}` |
| Acquisition by SHA-256, resumable, paced for Commons and parallel for whole-slide files | `app/base/acquire.py`, `data/base/acquired.json` |
| Offline validation, the floors with recorded shortfalls, the report and the coverage matrix | `app/base/validate.py`, `app/base/coverage.py`, `docs/collections/{base-report,coverage}.md` |
| The bake through the product's pipeline, and the verified, repeatable import | `app/base/bake.py`, `app/base/importer.py` |
| The contract field `slide.format_assumed` (migration 0007): the source does not record the physical slide | `app/contracts/ingest.py`, `app/db/migrations/versions/0007_format_assumed.py` |
| Wiki page 10 with its diagram (both themes checked), the guide, this record | `docs/` |

## Decisions

- **Every slide is chosen by looking at it.** A harvest never selects; it lists candidates whose licence is in the
  base policy and whose long side is at least 1000 pixels, on a numbered contact sheet. The curator writes one line
  per chosen image. Metadata cannot tell a microscope preparation from a figure plate, a drawing, an SEM image or a
  stereo photograph of a whole animal, and full-text pools are noisy (dossier 06).
- **Facts come from the source, not from the look of the image**, except one: interference colours on an extinct
  black ground are recorded as crossed polars. Everything else (the organism, a stain, the illumination) is read in
  the source's description or title; an image whose illumination can be neither read nor seen is left out. Labels
  photographed on NHM slides are read for hosts, localities and dates; a date that is not a calendar date is left
  out.
- **SEM images enter only as labelled external images** (`sem_external`), as dossier 06 allows; they are never
  presented as light microscopy.
- **The GBIF backbone is used as it is.** Names are resolved by strict match at the rank; a synonym is refused with
  its accepted key, and the pick then names the key and keeps the name as written. Homonym genera (*Hydra*,
  *Anomia*, *Dugesia*, *Haemoproteus*) are written by key after reading their lineage. An organism the backbone
  cannot hold at any rank the tree accepts (an unidentified fish, since the backbone has no ray-finned fish class) is
  left out rather than anchored wrongly.
- **Provenance is content-addressed.** Each file is stored under its SHA-256 and `acquired.json`, committed, maps
  each URL to what was retrieved. A published checksum (Zenodo MD5, OpenSlide SHA-256) is verified.
- **A shortfall is recorded, not hidden.** A collection under the floor fails validation unless it is listed with the
  finding that documents the searches (R-804). Reptiles is the one listed.
- **The server never bakes.** The bake is the product's own pipeline run on a workstation into a declared root; the
  import verifies every file against the manifest before it writes anything, and is repeatable (R-805, R-806).
- **CDC PHIL through its Commons mirror.** The plan named a PHIL adapter; a PHIL page serves only a small image and
  loads its description dynamically, so the public-domain PHIL items are taken from Commons, which mirrors them with
  the description, the photographer and the statement.
- **Supplementary sheets for open nodes.** After the first coverage matrix, files found by search were added on a
  sheet of their own (`search.additions`) rather than appended to category sheets, so the numbers already reviewed
  never move.
- **The whole-slide sources are the NMNH scans and the OpenSlide items whose tissue and organism are recorded.** The
  26 GB Prototaxites scan is left out (the tier-A budget of dossier 04); OpenSlide items without a recorded tissue
  (the CMU slides) and Zeiss CZI (not read by OpenSlide 4.0.1) are left out.
