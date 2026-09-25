# Changelog

All notable changes, newest first, grouped Added / Changed / Fixed / Removed. Versions are `X.XX.XXX` (the `VERSION`
file, the tags and this log); manifests carry the semantic form.

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
