# Changelog

All notable changes, newest first, grouped Added / Changed / Fixed / Removed. Versions are `X.XX.XXX` (the `VERSION`
file, the tags and this log); manifests carry the semantic form.

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
