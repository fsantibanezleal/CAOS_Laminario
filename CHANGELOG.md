# Changelog

All notable changes, newest first, grouped Added / Changed / Fixed / Removed. Versions are `X.XX.XXX` (the `VERSION`
file, the tags and this log); manifests carry the semantic form.

## [0.02.000] - 2026-09-28

### Added

- The imaging engine (`app/imaging/`): a reader for scanner formats (through OpenSlide), TIFF, ImageJ stacks and
  photographs that describes a file from its headers (levels, pixel size and its source, objective, label, macro
  and thumbnail images, focal planes with depths, the slide's size and the scan's position on it); limits applied
  before any decoding; one pyramidal BigTIFF per plane with its level-0 fidelity measured, a full-chroma fallback
  when quality 85 falls short, WebP kept only when smaller, and resolution tags only from a trustworthy pixel
  size; the z-plane policy; thumbnails and clean saving without EXIF; the scan placed on the macro photograph;
  the true-scale mount.
- Extended depth of field: variance selection and complex wavelet fusion ported from the EPFL plugin (Forster et
  al. 2004) and proven exact against its own output (100 percent of height-map pixels on its three sample
  stacks), fused in tiles for stacks of any size.
- Synthetic focal stacks with known focus, used to measure the methods; `scripts/bench_imaging.py` reproduces
  every measurement of the imaging wiki page.
- Wiki page "The imaging engine" with the pipeline diagram; the U2 design, requirements and verdict.
- The prerequisites check looks for libvips with OpenSlide; `LAMINARIO_VIPS_BIN`, `LAMINARIO_FIXTURES` and
  `LAMINARIO_TEST_TMP` are read from `.env`.

### Changed

- R-012, R-013, R-016 and R-019 restated with the measurements that required it (see the U2 requirements).

### Fixed

- A defect of the EPFL plugin is not carried over: its consistency checks swap width and height, which on
  non-square sizes makes its height maps three times less often right on stacks with known focus. The true
  sub-band geometry is the default; the plugin's convention remains available for comparison.

## [0.01.000] - 2026-09-25

### Added

- The ingestion contract (`app/contracts/ingest.py`): the slide case as typed models, every rejecting rule answering
  with the field and the expected range, rules across fields (custom sizes, coverslip fit, GBIF keys for taxa,
  the licence policy per origin, modality per micro image, planes and polarisation), and the three flags
  (`not_to_scale`, `gps_stripped`, `exif_date_mismatch`). `POST /api/slide-cases/validate` runs it without storing.
- The licence policy (`app/contracts/licences.py`): canonical URIs, the base-collection set and the wider
  contribution set.
- The catalog contract (`app/contracts/catalog.py`) and its builder: the record the web reads, with geoprivacy
  applied (obscured places reduced to a 0.2 degree cell and a stable public point, private places to nothing),
  media addresses, computed quality checks, the permalink and the QR payload. `GET /api/slides/{id}` and
  `GET /api/slides` (by collection node or anchor kind).
- The database: SQLAlchemy 2.0 models for `slide` and `asset`, SQLite in write-ahead-log mode with a busy timeout
  and enforced foreign keys on every connection, Alembic migrations, Crockford base-32 short ids resolved
  case-insensitively.
- The committed JSON Schemas of both contracts (`contracts/`), the exporter with its `--check` mode, the frontend
  workspace (React 19, Vite, TypeScript, Vitest) with the generated TypeScript types and the drift check; the web
  job in CI (contract drift, type check, build).
- Wiki pages for the data contracts (with the data-model diagram) and the database; the U1 feature design with
  its convergence verdict.

## [0.00.000] - 2026-09-24

### Added

- The product software design document (`docs/design/SDD.md`), written before any code and accepted: problem and
  non-goals, the ingestion and artifact contracts, the lanes, twelve processing methods with their acceptance
  criteria, the collection taxonomy and coverage floors, the evaluation oracle, the deploy driver, risks and kill
  criteria, and the requirements with the gate that verifies each.
- The repository base: the server skeleton with `GET /api/health` (product and version), settings from the
  environment, and the version read from `VERSION`.
- Guards: repository hygiene (no env, venv, slide, pyramid or database files, nothing over 5 MB, no local machine
  paths), template residue (including no Pages workflow), content standards, CI budget and the design-document
  gate, each tested against negative controls.
- Continuous integration on `develop` and `main` (lint and guards only).
- Numbered local scripts `00_install-prereqs`, `01_init` and `03_dev` in PowerShell and bash.
- The wiki: index, architecture overview with its diagram (light and dark), the run-locally guide, and the U0
  feature design.
