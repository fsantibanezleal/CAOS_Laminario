# Changelog

All notable changes, newest first, grouped Added / Changed / Fixed / Removed. Versions are `X.XX.XXX` (the `VERSION`
file, the tags and this log); manifests carry the semantic form.

## [0.05.000] - 2026-09-29

### Added

- Accounts (fastapi-users 15.0.5, ADR-0044): accounts and sessions in the app's own database, sessions as opaque
  tokens in an `HttpOnly`, `SameSite=Lax` cookie that sign-out invalidates at once; password reset with signed
  one-hour tokens.
- Invitation-only registration: single-use links valid seven days, stored only as their SHA-256, claimed atomically
  (one account per link under concurrent use), optionally bound to one address; no open registration route. The
  first admin is invited from the server's command line (`python -m app.accounts invite --role admin`).
- Roles contributor, identifier, curator and admin, and one capability table every route checks; curators invite
  up to identifier, admins manage invitations and accounts; the last admin keeps the role.
- The optional mail sender (SMTP with STARTTLS, a custom CA bundle for private relays): invitations and reset links
  are mailed when configured, otherwise shown once to the person who issued them.
- `POST /api/slide-cases`: contributors store validated cases as their drafts; a placement override needs a curator.
- State-changing requests from another origin are refused; reads stay open.
- Account, invitation and created-case records in the catalog contract and its TypeScript types; migration 0004.
- Wiki page "Accounts and roles" with its diagram, the fastapi-users framework card; the U6 design, requirements and
  verdict.

## [0.04.001] - 2026-09-29

### Added

- Framework cards (`docs/frameworks/`) for every library the product uses for its core work: libvips through pyvips,
  OpenSlide, iipsrv, pebble, tifffile, nginx, and the EPFL Extended Depth of Field plugin as the reference the
  port is measured against; each with the exact verified version, usage, how Laminario applies it, caveats and
  licence.
- The data-contract reference (`docs/data-contract/`): every field of the slide case and of the catalog records,
  generated from the committed JSON Schemas by `scripts/render_contract_docs.py`, with a `--check` mode in CI and
  a test; an overview of what is refused, what is flagged, and how missing and doubtful data are handled.

## [0.04.000] - 2026-09-29

### Added

- The processing worker (`python -m app.worker`): claims jobs from a durable queue in the catalog's SQLite
  database, runs each in a one-process `pebble` pool whose timeout kills the process, one job at a time,
  re-queues jobs a crash interrupted (failing them after three interruptions), and puts a running job back
  when asked to stop.
- The job journal (`job_event`): every step numbered per job; `GET /api/jobs/{id}` and the Server-Sent Events
  stream `GET /api/jobs/{id}/events`, which replays after `Last-Event-ID`, follows live and ends after the
  terminal event. Jobs have random public ids.
- The processing jobs: `process_asset` (source through the imaging engine to a measured pyramid, or a clean
  JPEG for macro photographs, asset marked ready with dimensions, bytes, SHA-256, PSNR and codec) and
  `fuse_stack` (both composites and the variance height map), queued once when a stack's last plane is ready;
  `probe` for health checks. Storage keys are content addresses, so reruns write the same bytes and a new
  source a new key.
- Operator commands `python -m app.jobs enqueue / status / list / wait`.
- `JobRecord` and `JobEventRecord` in the catalog contract and its TypeScript types; migration 0003.
- Wiki page "The processing worker" with its diagram; the U4 design, requirements and verdict.

### Changed

- Manifests leave height maps out of the painted images.

## [0.03.000] - 2026-09-29

### Added

- IIIF delivery. `info.json` served by the API with this deployment's public `id` and each asset's licence as
  `rights`; image requests passed to iipsrv; the base URI redirected; identifiers that are storage keys with
  their slashes encoded, read from the end of the path because web servers decode `%2F`.
- iipsrv 1.3, the official image pinned by digest, in `deploy/iipsrv/compose.yaml` (loopback, read-only store,
  read-only root, memory and CPU limits).
- The production nginx site in `deploy/nginx/laminario.conf`: tiles straight from iipsrv, cached 30 days on the
  data volume, each checked first with the API (`auth_request`, 60 s) so drafts and withdrawn images are never
  served; `info.json`, manifests and the API behind it.
- IIIF Presentation 3 manifests at `/api/slides/{id}/manifest`: a Canvas per ready image with its own `rights` and
  attribution, image services, `partOf` the collection node, `navPlace` by geoprivacy, `homepage`, `seeAlso`.
- The remote-asset contract (availability, protocol, rights, CORS, dimensions) and the link check
  `scripts/check_remote_iiif.py`; the IIIF version of a remote service is recorded (migration 0002).
- Gates with the pinned containers: tiles equal to the pyramid at every level, nginx cache hits and refusals;
  manifests validated against the IIIF validator's schema pinned by commit and hash.
- Wiki page "IIIF delivery" with its diagram; the U3 design, requirements and verdict.

### Changed

- The JPEG ladder of the pyramid writer climbs to Q95 when Q90 still misses 38 dB (a texture close to noise
  measured 37.5 dB at Q90 and 43.3 dB at Q95).
- `httpx2` is a runtime dependency; `jsonschema` a test one.

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
