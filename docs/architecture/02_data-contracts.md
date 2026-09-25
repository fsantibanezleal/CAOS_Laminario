# 02 · The two data contracts

![The slide case: ingestion contract, database, catalog contract, and the committed schemas with their TypeScript mirror](svg/data-model.svg)

A product is only real if data flows through enforced contracts. Laminario has two, and they are separate from
the tables: a submission and a catalog record are typed models whose JSON Schemas are committed; the tables are
the storage behind them.

## The ingestion contract

What a slide-case submission must satisfy before anything is stored. It runs in `POST /api/slide-cases/validate`
(nothing stored) and again when a case is created. Validation has three phases:

1. **Structure.** Types, vocabularies, ranges, lengths, patterns and partial dates, declared on each field with the
   text of what is expected. An error names the field and that text: `slide.format`, "one of: iso_76x26, ...".
2. **Rules across fields.** A custom format needs its size; a coverslip must fit on the slide; a taxon is referenced
   by its GBIF key; a host is an organism; the licence must be in the policy for the submission's origin; a
   micro image states its modality; a focal plane carries its stack, index and depth; a polarised image's modality
   matches its state; an imported asset carries its source; at most 200 planes per stack.
3. **Flags.** Conditions that are accepted but reported: a micro image without a pixel size (`not_to_scale`), a
   photo with GPS while the place is private (`gps_stripped`, the GPS is removed before storage), a photo taken
   more than a day from the collection date (`exif_date_mismatch`).

Rules that need a registry or the file itself are enforced where those exist: anchor resolution and placement
acceptance by the collection tree, readable headers and dimension limits by the imaging engine and the upload
verifier.

### The slide

| Field | Accepted |
|---|---|
| `format` | `iso_76x26` (76 x 26 mm, ISO 8037-1), `us_75x25`, `petro_27x46` (petrographic), `us_2x3in`, or `custom` with a size of 20 to 100 mm per side |
| `coverslip` | `none`, `18x18`, `22x22`, `22x40`, `22x50`, `24x50`, `24x60`, or `custom`; it must fit on the slide in some orientation |
| `preparation` | whole mount, section, smear, squash, strew, thin section, polished section, peel, cast, fluid mount |
| `stain`, `mountant` (80), `catalogue_number` (64), `label_note` (160), `preparer` (120) | text up to the length in parentheses |
| `prepared_on` | `YYYY`, `YYYY-MM` or `YYYY-MM-DD`, from 1600, not in the future |

### The specimen

| Field | Accepted |
|---|---|
| `anchor` | `kind` taxon, rock, mineral, crystal or material; `ref` (a taxon's is its GBIF usage key); `name`; optional `rank` |
| `collected_on` | a partial date, as above |
| `coordinates` | latitude -90 to 90, longitude -180 to 180, uncertainty at least 0 m |
| `geoprivacy` | `open`, `obscured` or `private` |
| `host` | a taxon anchor (for parasites and symbionts) |
| `type_status` | holotype, paratype, allotype, syntype, lectotype, paralectotype, neotype, topotype, other |

### Assets

| Field | Accepted |
|---|---|
| `family`, `role` | macro: `slide_overview`, `specimen`, `place`, `label`; micro: `single`, `pyramid`, `z_plane`, `polarised` |
| content | a contribution has exactly one of `upload_id` or `remote_iiif`; a base-collection asset has a `source` (URL, record id, retrieval date, SHA-256) |
| `licence` | see the policy below |
| `rights_holder` or `creator` | at least one |
| `pixel_size_um` | 0.05 to 50 micrometres per pixel; absent means "not to scale" |
| `modality` | brightfield, darkfield, phase contrast, DIC, polarised PPL, polarised XPL, reflected, fluorescence, or an external SEM image; required for micro assets |
| `plane` | for `z_plane`: index, depth in micrometres, stack name; at most 200 planes per stack |
| `polarisation` | for `polarised`: state `ppl` or `xpl` (the modality must match) and an angle 0 to 360 degrees |

### The licence policy

Licences are stored as canonical URIs (https, the licence path, a trailing slash, jurisdiction ports kept), so
`http://creativecommons.org/licenses/by/4.0` and `.../by/4.0/legalcode` are one licence.

| Origin | Accepted |
|---|---|
| base collection | CC0 1.0, Public Domain Mark 1.0, No Known Copyright, CC BY and CC BY-SA 2.0 to 4.0 including jurisdiction ports |
| contributions | the base set plus CC BY-NC 4.0 and CC BY-NC-SA 4.0 |

Anything else (all rights reserved, no-derivatives variants, unknown text) is refused with the list above as the
expected value.

## The catalog contract

The record the web reads, assembled from the rows, never copied from a submission. It carries the short id,
permalink and QR payload (the permalink in upper case, which encodes one QR version smaller), the slide's
physical format and coverslip in millimetres, the label fields, the anchor and host, the placement, computed
quality checks, the assets with their media addresses (a IIIF `info.json` for a pyramid or a remote service, a
plain URL for a photo), and the address of the slide's IIIF manifest.

### Geoprivacy

Applied when the record is built, so exact coordinates never leave the database for an obscured or private place:

| Setting | In the record |
|---|---|
| `open` | the stored point and its uncertainty |
| `obscured` | the 0.2 degree cell containing the point, and a public point inside it that depends only on the cell and the slide's id (the same on every request, and unrelated to where the true point lies in the cell) |
| `private` | no point and no cell; only the locality text |

For a stored point $(\varphi, \lambda)$ the cell is $[\varphi_0, \varphi_0 + 0.2) \times [\lambda_0, \lambda_0 + 0.2)$
with $\varphi_0 = 0.2\lfloor \varphi / 0.2 \rfloor$, $\lambda_0 = 0.2\lfloor \lambda / 0.2 \rfloor$, and the public
point is $(\varphi_0 + 0.2u, \lambda_0 + 0.2v)$ with $u, v \in [0, 1)$ derived from the SHA-256 of the short id.
This follows the obscuring iNaturalist applies to sensitive locations.

### Quality checks

Computed from what is stored, never asserted: every asset carries a licence and, for the base collection, a
source; every micro image has a pixel size; every micro image states its modality; the slide has at least one
macro and one micro asset. A slide that passes all of them is `needs_id` until the community agrees on its
identification (`verified`); otherwise it is `reference`.

## The committed schemas and their mirror

`scripts/export_contracts.py` writes `contracts/ingest.schema.json` and `contracts/catalog.schema.json`; a test
and a CI step fail when they differ from the models. `frontend/scripts/generate-contract-types.mjs` turns them
into `frontend/src/contract/*.ts`, and `check-contract-drift.mjs` fails the build when the committed TypeScript
differs from what the schemas produce. The web imports only these types.
