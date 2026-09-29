# Changelog

All notable changes, newest first, grouped Added / Changed / Fixed / Removed. Versions are `X.XX.XXX` (the `VERSION`
file, the tags and this log); manifests carry the semantic form.

## [0.12.000] - 2026-09-29

### Added

- The account places: sign in, join from an invitation link, ask for and complete a password reset; the masthead
  names the account and offers Contribute to those who may.
- The contribute places: a contributor's cases, and the case editor in six sections with the slide drawn to scale;
  the anchor combobox, the parts vocabulary (`GET /api/vocab/parts`), the point map, geoprivacy, the drawer the
  tree suggests, the calibration of a pixel size on a stage micrometer.
- A code and parameters on every validation error and flag, worded in EN and ES by the interface.
- The case lifecycle: draft, processing, published, back to draft with the reason; a contributor's drafts
  listed, reopened, changed and deleted (migration 0010).
- A photograph's position read and shown before upload, removed with its XMP in the browser for a private case
  (JPEG, PNG, WebP, TIFF), and refused by the server if it stays.
- Uploads with Uppy over tus; verification and processing followed by their events; each image keeps its
  original's SHA-256, shown on its slide.
- `frontend/gates/contribute.mjs`, end to end on CMU-1 and a real photograph with GPS; wiki page 14.

### Fixed

- The `/files` proxy keeps the page's host, so tusd's upload addresses are the page's own (F-044).

## [0.11.000] - 2026-09-29

### Added

- The slide place: the slide as an object drawn by the server from one layout in millimetres (the frosted label end,
  the coverslip, the data label, the mount window), inlined in the room's colours; its labels printed on an A4 sheet at
  1:1 with Courier Prime embedded, the outline measuring the format; the QR (version 3, alphanumeric, error
  correction M) of the permalink in upper case; reading the label beside the scanner's photograph of the real one;
  the photographs; the record; where every image came from, with the original's SHA-256.
- Plain images (`/media/<key>`) for published slides, checked as the tiles are.
- The stage: OpenSeadragon over each image's IIIF info.json, objectives from the pixel size with digital zoom said
  as such, the scale bar of the 1-2-5 series, focal planes named by depth with the all-in-focus composites and the
  height map, a polarised pair faded one over the other and turned in quarter turns.
- Annotations as W3C Web Annotations on one image (migration 0009): Annotorious draws rectangles and polygons, the
  server keeps text bodies and plain shapes and sets the id, target, creator and dates.
- `GET /api/session`, a 200 for visitors too.
- The QR, scale-bar and stage gates; wiki page 13 with its diagram; the U11 design and requirements.

## [0.10.000] - 2026-09-29

### Added

- The places a visitor walks: the realms with their collections as cabinets, a cabinet's drawers, a drawer's tray
  (slides at their format's proportion, one scale per tray, label end first), filters with faceted counts kept in
  the address, search, the map; wouter routing with the focus on each place's heading and the scroll restored on
  back.
- A slide's country, stated by its source or implied by its coordinates against Natural Earth 1:50m shapes, named
  in English and Spanish from Unicode CLDR 48.2.2; the base slides placed in the countries their sources state.
- FTS5 search over a text composed from the anchor, the tree's names in both languages, the locality, the catalogue
  number and the short id, kept in step by triggers (migration 0008); disjunctive facet counts; the map's countries
  and points after geoprivacy; the country shapes.
- The map over a pinned, verified Protomaps extract served with byte ranges, in the rooms' colours, labelled in
  Laminario Sans, with the country list as its keyboard equivalent and a fallback without the basemap.
- The walk gate; wiki page 12 with its diagram; the U10 design and requirements.

## [0.09.000] - 2026-09-29

### Added

- The visual system (`docs/design/visual-system.md`): tokens in OKLCH for the daylight and lamp-lit rooms with 18
  collection hues, generated as sRGB and checked for contrast (164 pairs).
- Three faces built from pinned upstream files: Laminario Sans (a renamed Latin subset of Source Sans 3), Fraunces
  and Courier Prime, each with its OFL licence text.
- The room and the language painted from the first frame; typed EN and ES catalogues over Intl, with calendar dates
  in UTC.
- Interface glyphs, the primitives with their states, the specimen place (`/design`).
- The fit, motion and states gates; wiki page 11 with its diagram; the U9 design and requirements.

## [0.08.000] - 2026-09-29

### Added

- The base collection: 505 slides over the 18 collections from open sources (Wikimedia Commons, the Natural History
  Museum's Data Portal, Smithsonian Open Access, Zenodo's NMNH focal stacks, the OpenSlide test data), 14
  whole-slide scans, a registered polarised pair for every rock family, every image with its licence, author or
  rights holder, source record, retrieval date and SHA-256; Reptiles hold seven, the open supply recorded (F-031).
- The base-collection lane (`python -m app.base`): harvest with review sheets, the picks notation, the lock with
  GBIF names and lineages (`data/base/taxa.json`, no later step calls GBIF), resumable acquisition into the vault with
  SHA-256, offline validation through the same contract and tree checks a contribution meets (the report and the
  coverage per collection and sub-collection in `docs/collections/`), the bake through the product's own pipeline
  into a declared root, and the import that refuses a failed or tampered bake and adds nothing twice.
- The Smithsonian Open Access adapter (CC0), with Wilson Bentley's snow crystals typed by his own categories.
- `slide.format_assumed` (migration 0007): a format the source does not record is assumed and said so.
- Wiki page 10 with its diagram, the operator guide, the U8 design and requirements.

### Changed

- The fusion timeout is a setting (two hours by default; the base bake allows six).
- A Commons credit keeps the people and drops the file page's furniture (F-046); an OpenSlide sample credits whom
  OpenSlide's index credits (F-047).

### Fixed

- NDPI focal planes are read without libtiff's allocation guard (a plane is one very large strip).
- The job process runs with the worker's settings, not the environment's; the bake fails when a job fails.
- Whole-slide files take the extension of the source's file name, so the reader sees an NDPI's focal planes.
- Samples the pipeline cannot read are replaced: DICOM 3DHISTECH-2 (over the 200,000 px guard, F-043) by Philips-2,
  Ventana-1 (tiles joined LEFT, which no OpenSlide release reads, F-045) by Philips-3.

## [0.07.000] - 2026-09-29

### Added

- The collection tree: 3 realms, 18 collections, 130 sub-collections and groups (191 nodes, the ten vertebrate organ
  systems shared by five collections), each with EN and ES names and descriptions, an icon and a rule; the
  generated reference `docs/collections/tree.md`.
- Anchor vocabularies: the GBIF backbone (134 tree taxa locked with their lineages), 6,200 IMA mineral species with
  Nickel-Strunz codes from Wikidata and 27 group names, 365 rock names from the BGS Rock Classification Scheme and
  meteorite classes, crystal origins with snow-crystal categories, materials, parts; the build and check scripts.
- Placement: rules over kind, taxa with exclusions, vocabulary paths, part and preservation, with priorities; the
  suggestion, its path and the accepting nodes; the tree guard (integrity, reachability, sibling overlaps).
- The GBIF taxon cache (table `taxon`, migration 0006); submissions resolve the anchor and the host and check the
  placement, with a curator's override and reason; 503 when GBIF does not answer.
- `GET /api/collections`, `/api/collections/{id}`, `/api/collections/{id}/iiif` (IIIF Presentation 3 Collections,
  the `partOf` of every manifest), `/api/facets`, `/api/anchors/search`, `POST /api/placement`; host views in
  `GET /api/slides?node=`.
- 186 hand-drawn icons in one sprite with EN and ES titles, their build and gate, the contact sheet.
- Wiki page "The collection tree" with its diagram, the GBIF API card, the collections docs, the U7 design,
  requirements and verdict.

### Changed

- The ingestion contract gains `specimen.part`, `specimen.preservation` and `anchor.classification`; the catalog
  record carries them; the stored anchor is its canonical form.
- The standard test payload's host key is Thomomys (2439381); the earlier key was Spermophilus columbianus.

## [0.06.000] - 2026-09-29

### Added

- Resumable uploads (tus 1.0) through tusd v2.10.1: the pre-create hook, with the session cookie forwarded,
  refuses before any byte is stored when the uploader does not own the draft or the image, the size is undeclared
  or over 30 GB, the account's quota (40 GB, 20 whole-slide images) would be exceeded, or a whole-slide image
  arrives while the data volume is over 90 percent full; each refusal carries its status and reason.
- The verification job: size, SHA-256, the type sniffed from the bytes (JPEG, PNG, WebP, TIFF, BigTIFF, DICOM,
  ZIP archives holding MRXS, VSI or DICOM slides), safe unpacking, a header the reader opens; accepted files go to
  the source store and to processing, refused ones are deleted from quarantine with the reason.
- `GET /api/uploads` and `GET /api/uploads/{id}`; the upload record in the catalog contract and TypeScript;
  migration 0005.
- `deploy/tusd/compose.yaml` (pinned image, loopback, read-only) and nginx's `/files/` location.
- Wiki page "Uploads" with its diagram, the tusd framework card; the U5 design, requirements and verdict.

### Changed

- `Worker.run` accepts a deadline (tests use it; the service runs without one).

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
