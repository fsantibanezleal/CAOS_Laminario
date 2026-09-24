# Laminario · software design document (product)

Written 2026-09-23 after the research and the plan and before any code; reviewed and accepted by the
owner on 2026-09-24. It is the design the code follows. Each non-trivial unit adds a feature design
under `docs/design/features/<unit>/` (requirements in EARS, design, tasks) before its code, and every
requirement names the gate that fails when it is violated.

The guard `scripts/check_sdd.py` fails when a requirement in a fenced block names a gate file or test
that does not exist. So this document fences only the requirements whose gates exist today; each
unit's requirements are listed in section 9 as indented blocks and move, verbatim, into that unit's
`requirements.md` the day the unit starts. The convergence verdict of each unit lists every one of
its requirements with its gate result.

## 1. Problem and non-goals

**Problem.** Microscope slides are among the most numerous objects in natural-history and teaching
collections (the Natural History Museum, London, alone holds about 2.5 million), and a growing share is digitised openly, but they
are published as records in museum portals or as files in data deposits. Nobody can browse them as
slides, across kingdoms and across rocks, minerals and crystals, or add their own. Laminario answers:
*show me this kind of thing under the microscope, as a real slide, with where it came from and under
which licence; and let me add mine.*

**Non-goals** (things a reader would reasonably assume, and that are out):
1. Automated identification, diagnosis, or any scored comparison of methods.
2. Registration of unaligned polarisation images: PPL/XPL pairs and rotation series are accepted only
   when already registered by their source; unregistered pairs are stored as separate assets.
3. Fluorescence multichannel compositing and volumetric viewing.
4. An in-app camera QR scanner (phones open the QR natively).
5. A geocoding service; reverse lookup of place names.
6. Independent verification of museum identifications in the base collection: the determination on
   the source record is recorded as such.
7. Mirroring every remote IIIF image: remote services are referenced when they meet the remote-asset
   contract.
8. Payments, private collections, organisations or projects as tenants.
9. Open self-sign-up: contributors are invited by an admin or a curator. Visitors need no account.

## 2. Contracts

### 2.1 Ingestion contract (raw to processing): the slide case

A submission (from the contribute flow or from the base-collection lock) is accepted only if it
validates against this contract. Types are Pydantic models in `app/contracts/ingest.py`, with JSON
Schema exported for the frontend.

| Field | Type and range | Policy when violated |
|---|---|---|
| `slide.format` | `iso_76x26` \| `us_75x25` \| `petro_27x46` \| `us_2x3in` \| `custom{w_mm,h_mm}` with 20 <= w, h <= 100 | reject |
| `slide.coverslip` | `none` \| `18x18` \| `22x22` \| `22x40` \| `22x50` \| `24x50` \| `24x60` \| `custom{w_mm,h_mm}` fitting inside the slide | reject |
| `slide.preparation` | one of 10: whole mount, section, smear, squash, strew, thin section, polished section, peel, cast, fluid mount | reject |
| `slide.stain` | free text <= 80 plus optional controlled term | reject if longer |
| `slide.prepared_on`, `specimen.collected_on` | ISO 8601 date, year or year-month allowed; not in the future; not before 1600 | reject |
| `specimen.anchor` | `{kind: taxon\|rock\|mineral\|crystal\|material, ref, name}`; `taxon.ref` = GBIF usage key resolved against the cached backbone; `mineral.ref` = IMA-CNMNC name; `rock.ref` = BGS RCS term; `crystal.ref` = system plus origin; `material.ref` = controlled term | reject when unresolved; a contributor may submit `taxon` at any rank |
| `specimen.coordinates` | lat in [-90, 90], lon in [-180, 180], uncertainty_m >= 0 | reject |
| `specimen.geoprivacy` | `open` \| `obscured` \| `private` | reject |
| `specimen.host` | optional taxon anchor | reject when unresolved |
| `placement.node` | a collection node whose rule accepts the anchor, or a curator override with reason | reject (contributor), accept with audit (curator) |
| `assets` | at least one; each `{family: macro\|micro, role, file, licence, rights_holder or creator, pixel_size_um?, modality?, plane?}` | reject |
| `asset.licence` | URI in the policy set: CC0, public domain mark, NKC rights statement, CC BY 2.0 to 4.0, CC BY-SA 2.0 to 4.0, and for contributions also CC BY-NC and CC BY-NC-SA | reject |
| `asset.file` | sniffed type in: JPEG, PNG, WebP, TIFF/BigTIFF, SVS, NDPI, MRXS (zip), SCN, VSI (zip), DICOM WSI (zip), Philips TIFF; header readable by libvips or OpenSlide | reject |
| image dimensions | 64 to 200,000 px per side; at most 20 gigapixels per plane for uploads | reject (decompression-bomb guard) |
| `asset.pixel_size_um` | 0.05 to 50 um per pixel, from file metadata or declared or calibrated | outside range: reject; absent: accept, flag "not to scale" |
| `asset.plane` | z index and depth in um; all planes of one stack share dimensions; at most 200 planes | reject |
| EXIF | GPS present with geoprivacy `private` | accept, strip GPS before storage, flag |
| EXIF date vs declared date | disagree by more than a day | accept, flag for the contributor |
| imported source | `source.url`, `source.record_id`, `retrieved_on`, `sha256` of retrieved bytes | reject if any is missing |

### 2.2 Artifact contract (processing to web)

1. **Pyramid file**, one per plane and modality: BigTIFF, tiled 512 x 512, JPEG Q85 (or WebP Q80 when
   measured smaller for that asset), levels down to at most 512 px on the long side, sRGB, resolution
   tags set from the pixel size when known; SHA-256 and byte size recorded.
2. **Catalog record**, the API's `Slide` JSON: identity (`id`, `short_id`, `permalink`), format and
   coverslip, label fields, anchor (kind, ref, name, rank), placement path, quality badge with each
   computed check, community status, assets (family, role, IIIF `info.json` URL or image URL, width,
   height, `pixel_size_um` or null, planes, modality, licence URI and short name, rights holder,
   creator, source block), relations, manifest URL. Pydantic in `app/contracts/catalog.py`; the
   TypeScript type is generated from its JSON Schema and committed; a drift fails the frontend build.
3. **IIIF Image API 3** `info.json`, served by iipsrv, with `rights` rewritten by nginx from the asset
   licence (iipsrv does not know it).
4. **IIIF Presentation 3 Manifest** per slide: one Canvas per micro asset plane and per macro asset,
   `rights` and `requiredStatement` per Canvas, `partOf` the collection node.
5. **Remote-asset contract** (referenced IIIF): the remote `info.json` answers, declares `rights` in the
   policy set, allows CORS, and its dimensions match those recorded; checked at import and by a local
   link-check command.

## 3. Lanes, with their basis

| Work | Lane | Basis |
|---|---|---|
| Base-collection acquisition and curation | offline, local machine, release operation | 35 GB of source downloads and hours of pyramiding; must not run in CI or deploy |
| Pyramiding, EDF composite, thumbnails, label and QR render for uploads | server worker, request time | measured 30 s for 1.5 GP locally; GB-scale files cannot be processed in a browser; libvips and OpenSlide are native |
| Tile delivery | server, iipsrv behind nginx cache | one file per plane (section 2.2) needs a tile server |
| EXIF read, GPS preview and stripping choice | browser | lets the contributor see and remove location before any byte leaves the device; cost measured at U12 (gate below) |
| Viewing (OpenSeadragon), map (MapLibre + PMTiles) | browser | standard clients of the served artifacts |
| Base-collection deploy | rsync of the verified pyramid store plus an import command reading the bake manifest | deploy verifies and imports, never re-bakes |

## 4. The method ladder, with an acceptance criterion per method

"Method" here means each processing operation the product promises. There is no learned method.

| Id | Method | Implemented when |
|---|---|---|
| M1 | Reader (libvips + OpenSlide) | opens every CC0 fixture format in the fixture matrix and returns dimensions, levels, pixel size and associated images equal to the vendor metadata |
| M2 | Pyramid writer | level-0 PSNR against the decoded source >= 38 dB (mean over 32 seeded 512 px regions) for JPEG Q85; level count = ceil(log2(max side / 512)) + 1; file opens in libvips and in iipsrv |
| M3 | Z-plane policy | deterministic indices (both ends, evenly spaced, unique), whole stack kept when <= 500 MB, depths recorded |
| M4a | EDF baseline, variance selection | per-pixel plane of maximum local variance, smoothed decision map; composite sharpness (Tenengrad) >= 0.95 x the sharpest single plane on the three reference stacks |
| M4b | EDF wavelet fusion with sub-band consistency (Forster et al. 2004) | SSIM against the EPFL plugin's complex-wavelet output >= 0.90 on the three reference stacks, and >= M4a's SSIM |
| M5 | Derivatives (thumbnails, macro crop under the coverslip, true-scale mount) | exact sizes; true-scale mount width = specimen width in mm / slide width in mm, within 1 % |
| M6 | Label and QR renderer | decoding the rendered label image returns exactly the permalink; SVG and PDF print at 76.0 x 26.0 mm (or the format) within 0.1 mm |
| M7 | Placement rule engine | every node rule resolves; suggestions deterministic; sibling overlaps without priority fail the tree guard |
| M8 | Community agreement | community anchor = the deepest node on which more than 2/3 of identifications agree; verified on a scenario table |
| M9 | Quality checks | each check computed from stored data; badge derived only from checks |
| M10 | IIIF manifest generator | every generated manifest validates against the pinned IIIF Presentation 3 JSON Schema |
| M11 | Upload verifier | sniffing, size, checksum and bomb guard reject every negative fixture and accept every positive one |

## 5. Case taxonomy and coverage matrix

The "cases" are slides placed in the collection tree (3 realms, 18 collections, 129 sub-collections
and groups), documented with the reason each node exists in `docs/collections/`. The base-collection
coverage matrix is generated from the catalog and committed as `docs/collections/coverage.md`: per
collection, slide count (>= 12), sub-collections covered, WSIs, z-stacks, PPL/XPL pairs, licences. The
release fails if a floor is not met: >= 300 slides, >= 14 WSIs, >= 1 PPL/XPL pair per rock family,
every sub-collection with a real candidate covered, the rest shown as open for contribution.

## 6. The evaluation oracle

- **Imaging fidelity**: pixels of the decoded source at level 0 (M2) and the EPFL reference plugin
  for EDF (M4b). Trustworthy because both are independent of our code; the EPFL plugin is the published
  reference implementation of the cited method.
- **Tile correctness**: a tile fetched from iipsrv equals, after decoding, the same region cropped by
  libvips from the pyramid (max absolute difference <= 2 per channel, allowing re-encode rounding).
- **Licence and provenance**: the value read from the source record at acquisition, with the record URL
  and hash kept. Limitation: a source can change its record later; the local link-check command
  re-reads and reports differences, it does not silently update.
- **Anchors**: GBIF resolution by usage key; IMA list membership; RCS term membership.
  Limitation: the scientific determination itself is the source's (non-goal 6).
- **Interface**: pointer-driven browser gates on the built site and on production, both themes, both
  languages, desktop and 360 px phone, with measured viewport fit and QR decode from a screenshot.

## 7. Deploy driver

Target: a Linux server (4 vCPU, 8 GB RAM) serving `https://laminario.ml.fasl-work.com`, with the slide
store, the upload quarantine and the tile cache on a dedicated 100 GB block volume mounted at
`/srv/laminario`. Driver measurements: server state and accounts rule out static hosting; the base
collection's measured payload (about 13 GB, worst case 16 GB) plus upload working room (about 10 GB)
fits the volume with headroom, and keeps the server's root disk for the software. Alert at 80 GB used;
new whole-slide uploads refused at 90 GB until the volume is resized (it grows in place).

## 8. Risks and kill criteria

| Risk | Kill or change criterion |
|---|---|
| iipsrv misbehaves with libvips BigTIFF pyramids | if the tile gate fails on the CC0 fixtures after configuration fixes, the affected assets are served as a static IIIF level-0 export, and that is recorded |
| The EDF composite does not match the reference | z-stacks ship without the composite, and that is stated; a composite that fails its gate is never shipped |
| Server capacity (4 shared vCPU) | one heavy job at a time; if a 1.5-gigapixel pyramid takes over 10 minutes on the server, large uploads get longer timeouts and contributors see the measured time |
| Licence errors in the base collection | an asset without a verified licence is removed before release; a takedown path is documented |
| Abuse of contributions | contributors are invited; moderation tools must pass their gate before contributions are shown publicly |
| A format fails the tile-correctness oracle after fixes | that format is refused at ingestion, and the interface says so, rather than served wrong |

## 9. Requirements

Each requirement names the gate that fails when it is violated.

### Product level, gates present from U0

```
R-001  THE repository SHALL pass the content guards (English only, no em-dash, no emoji) on every tracked product file.
       Gate: scripts/check_content_standards.py

R-002  THE repository SHALL NOT track a .env file, a virtual environment, source slide files or pyramid files.
       Gate: scripts/check_repo_hygiene.py

R-003  THE CI workflows SHALL trigger only on push to develop and main and on workflow_dispatch, with a concurrency group and a timeout per job, and SHALL NOT run the test suite or any processing.
       Gate: scripts/check_ci_budget.py

R-004  THE repository SHALL NOT carry a GitHub Pages deploy workflow.
       Gate: scripts/check_template_residue.py
```

### Unit requirements (moved verbatim into each unit's `requirements.md` when it starts)

#### U1 contracts

    R-005  WHEN a submission violates any rejecting rule of the ingestion contract, THE API SHALL reject it with HTTP 422 naming the field and the expected range.
           Gate: tests/contracts/test_ingest_contract.py::test_every_rejecting_rule_names_field_and_range

    R-006  WHEN a submission carries a flagging condition of the ingestion contract, THE API SHALL accept it and return the flags.
           Gate: tests/contracts/test_ingest_contract.py::test_flagging_rules_accept_and_report

    R-007  THE generated TypeScript catalog types SHALL equal the types generated from the current catalog JSON Schema.
           Gate: frontend/scripts/check-contract-drift.mjs

#### U2 imaging engine

    R-010  WHEN a file of any format in the fixture matrix is read, THE reader SHALL return dimensions, level count, pixel size and associated images equal to the vendor metadata.
           Gate: tests/imaging/test_reader.py::test_fixture_matrix_metadata

    R-011  THE pyramid writer SHALL produce a tiled BigTIFF with 512 px tiles and ceil(log2(max side / 512)) + 1 levels.
           Gate: tests/imaging/test_pyramid.py::test_level_structure

    R-012  THE pyramid writer SHALL reproduce the source at level 0 with mean PSNR of at least 38 dB over 32 seeded 512 px regions at JPEG Q85.
           Gate: tests/imaging/test_pyramid.py::test_level0_fidelity

    R-013  WHEN pixel size is known, THE pyramid writer SHALL write it into the TIFF resolution tags.
           Gate: tests/imaging/test_pyramid.py::test_resolution_tags

    R-014  WHEN a z-stack's full pyramid set exceeds 500 MB, THE processor SHALL keep 11 evenly spaced planes including both ends and record their original indices and depths.
           Gate: tests/imaging/test_zpolicy.py::test_resample_indices_and_depths

    R-015  WHEN a z-stack is processed, THE processor SHALL produce a variance-selection composite whose Tenengrad sharpness is at least 0.95 of the sharpest plane on each reference stack.
           Gate: tests/imaging/test_edf.py::test_variance_baseline_sharpness

    R-016  WHEN a z-stack is processed, THE processor SHALL produce a wavelet-fusion composite with SSIM of at least 0.90 against the EPFL reference output and not lower than the baseline's.
           Gate: tests/imaging/test_edf.py::test_wavelet_parity_with_reference

    R-017  IF an image exceeds 200,000 px on a side or 20 gigapixels in a plane, THEN THE processor SHALL refuse it before decoding pixels.
           Gate: tests/imaging/test_guards.py::test_decompression_bomb_refused

    R-018  THE served derivatives SHALL carry no EXIF GPS data.
           Gate: tests/imaging/test_derivatives.py::test_no_gps_in_served_files

    R-019  THE true-scale mount SHALL occupy the specimen's physical width divided by the slide width, within 1 percent.
           Gate: tests/imaging/test_derivatives.py::test_true_scale_mount

#### U3 delivery

    R-020  WHEN a tile is requested from the IIIF service, THE tile SHALL equal the libvips crop of the same region within 2 levels per channel after decoding.
           Gate: tests/delivery/test_iiif_tiles.py::test_tile_equals_crop

    R-021  THE IIIF info.json served for an asset SHALL declare that asset's licence as rights.
           Gate: tests/delivery/test_iiif_tiles.py::test_rights_rewritten_per_asset

    R-022  THE manifest generator SHALL produce Presentation 3 manifests that validate against the pinned JSON Schema.
           Gate: tests/delivery/test_manifest.py::test_manifest_validates

    R-023  WHEN a remote IIIF asset is imported, THE importer SHALL verify availability, rights, CORS and dimensions, and SHALL reject it otherwise.
           Gate: tests/delivery/test_remote_iiif.py::test_remote_asset_contract

#### U4 worker

    R-030  WHEN the worker restarts while a job is running, THE worker SHALL re-queue the job and complete it with the same outputs.
           Gate: tests/worker/test_queue.py::test_restart_requeues_and_completes

    R-031  IF a job exceeds its timeout, THEN THE worker SHALL kill its process and mark the job failed with the reason.
           Gate: tests/worker/test_queue.py::test_timeout_kills

    R-032  WHEN a client reconnects to a job's event stream with a last event id, THE API SHALL replay every later event in order.
           Gate: tests/worker/test_sse.py::test_replay_after_reconnect

    R-033  THE worker SHALL run at most one heavy job at a time.
           Gate: tests/worker/test_queue.py::test_single_heavy_job

#### U5 uploads

    R-040  WHEN an upload is interrupted and resumed, THE upload SHALL complete with the original SHA-256.
           Gate: tests/uploads/test_tus.py::test_resume_after_interruption

    R-041  IF an upload's sniffed type is not in the ingestion contract, THEN THE system SHALL delete it from quarantine and report the type.
           Gate: tests/uploads/test_tus.py::test_disallowed_type_rejected

    R-042  IF an upload would exceed the contributor's byte or WSI quota, THEN THE hook SHALL refuse creation.
           Gate: tests/uploads/test_tus.py::test_quota_refused

    R-043  WHILE the data volume holds more than 90 percent of its size, THE system SHALL refuse new WSI uploads and say why.
           Gate: tests/uploads/test_tus.py::test_tier_a_budget_blocks_wsi

#### U6 accounts

    R-050  THE system SHALL create an account only through a valid, unexpired, unused invitation issued by an admin or curator.
           Gate: tests/accounts/test_accounts.py::test_registration_requires_invitation

    R-051  WHERE a mail sender credential is configured, THE system SHALL mail invitations and password-reset links through it; otherwise it SHALL show the link to the issuing admin only.
           Gate: tests/accounts/test_accounts.py::test_mail_adapter_against_local_sink

    R-052  THE API SHALL enforce roles: visitor reads, contributor submits, identifier identifies, curator moderates and overrides placement, admin manages invitations.
           Gate: tests/accounts/test_roles.py::test_role_matrix

#### U7 tree and icons

    R-060  THE collection tree SHALL give every node a rule, an EN and ES name, an EN and ES description and an icon, and every icon SHALL belong to a node or a facet.
           Gate: tests/collections/test_tree.py::test_tree_integrity

    R-061  IF two sibling rules overlap without a priority, THEN THE tree check SHALL fail.
           Gate: tests/collections/test_tree.py::test_sibling_overlap_needs_priority

    R-062  WHEN an anchor is given, THE placement engine SHALL return the same suggestion every time.
           Gate: tests/collections/test_placement.py::test_deterministic_suggestion

#### U8 base collection

    R-070  THE base collection SHALL hold at least 300 slides, at least 12 per collection and at least 14 whole-slide images.
           Gate: tests/base/test_base_collection.py::test_floors

    R-071  EVERY base-collection asset SHALL carry licence, rights holder or creator, source URL, record id, retrieval date and SHA-256, and its licence SHALL be in the base policy set.
           Gate: tests/base/test_base_collection.py::test_asset_provenance

    R-072  THE base collection SHALL contain at least one registered PPL/XPL pair per rock family.
           Gate: tests/base/test_base_collection.py::test_polarised_pairs

    R-073  THE base-collection bake SHALL write only inside its declared output root, and tests SHALL write only in temporary directories.
           Gate: tests/base/test_bake_sandbox.py::test_tests_never_write_canonical_outputs

#### U9 to U15 interface

    R-080  THE interface SHALL show no horizontal page scroll at 360, 768, 1280 and 1920 px wide on every place, in both themes and both languages.
           Gate: frontend/gates/fit.mjs

    R-081  THE design tokens SHALL give every text and icon colour a contrast ratio of at least 4.5 to 1 (3 to 1 for large text and icons) against its background in both themes.
           Gate: frontend/scripts/check-contrast.mjs

    R-082  WHEN the rendered slide label is screenshotted, decoding its QR SHALL return exactly the slide permalink.
           Gate: frontend/gates/qr.mjs

    R-083  WHEN a label is printed, THE printed slide SHALL measure the format size within 0.1 mm.
           Gate: tests/labels/test_print.py::test_print_dimensions

    R-084  WHEN a visitor clicks from the landing place, THE visitor SHALL reach every place (realm, cabinet, drawer, slide, stage, contribute, identify, profile, about) with the pointer only.
           Gate: frontend/gates/mousewalk.mjs

    R-085  WHILE prefers-reduced-motion is set, THE interface SHALL run no transition longer than 0 ms except opacity.
           Gate: frontend/gates/motion.mjs

    R-086  WHEN a micro asset has a pixel size, THE stage viewer SHALL show a scale bar whose length matches the physical distance within 1 percent at every objective step.
           Gate: frontend/gates/scalebar.mjs

    R-087  WHEN a contributor adds a photo with GPS, THE contribute flow SHALL show the location before upload and SHALL strip it when geoprivacy is private.
           Gate: frontend/gates/contribute.mjs

    R-088  THE agreement rule SHALL set the community anchor to the deepest node on which more than two thirds of identifications agree.
           Gate: tests/community/test_agreement.py::test_scenario_table

    R-089  EVERY interface string SHALL exist in EN and ES.
           Gate: frontend/scripts/check-i18n.mjs

#### U16 deploy

    R-090  WHEN the production gate suite runs against https://laminario.ml.fasl-work.com, THE suite SHALL pass every place, theme and language and SHALL verify it is talking to Laminario by its version endpoint.
           Gate: frontend/gates/production.mjs

    R-091  THE production host SHALL bind the API, the worker's health endpoint, tusd and iipsrv to loopback only.
           Gate: scripts/check_host_bindings.sh

## 10. Convergence

Each unit ends with its verdict in `docs/design/features/<unit>/tasks.md`: every requirement above that
belongs to the unit, its gate, and the gate's result on that commit. A red gate is listed, not omitted.
