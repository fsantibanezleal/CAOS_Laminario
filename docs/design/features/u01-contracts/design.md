# U1 · Data model and contracts · design

## What the unit delivers

The slide case as data, in four layers that never mix:

| Layer | Module | Role |
|---|---|---|
| Ingestion contract | `app/contracts/ingest.py` | What a submission must satisfy before anything is stored. Pydantic models; every rejecting rule names the field and the expected range; flagging rules accept and report. |
| Licence policy | `app/contracts/licences.py` | The accepted licences as canonical URIs, one set for the base collection and a wider one for contributions. |
| Catalog contract | `app/contracts/catalog.py` | The record the web reads for a slide and its assets. Built from the database, never from a submission; it applies geoprivacy. |
| Database | `app/db/` | SQLAlchemy 2.0 models, SQLite in write-ahead-log mode, Alembic migrations, short ids. |

Plus `POST /api/slide-cases/validate`, which runs the ingestion contract without storing anything: the contribute
flow (U12) and the base-collection pipeline (U8) both use it before they send files.

## Decisions

- **SQLAlchemy 2.0 declarative models, not SQLModel.** The account library (fastapi-users, U6) builds its user
  table on a SQLAlchemy declarative base, and its adapter requires SQLAlchemy below 2.1, so the whole schema uses
  one declarative base and SQLAlchemy 2.0.54. The API talks to the database asynchronously (aiosqlite); the
  worker (U4) uses the synchronous driver on the same file.
- **Contracts are separate from tables.** A submission and a catalog record are Pydantic models; tables are
  SQLAlchemy models. The catalog record is assembled from rows, so a column can change without breaking the web,
  and a contract change is visible in the committed JSON Schemas.
- **Tables arrive with their units.** U1 creates `slide` and `asset`. Users and invitations (U6), jobs and their
  events (U4), uploads (U5) and identifications (U13) come with their own migrations.
- **Rules that need a registry or a file are enforced where the registry or file exists.** Anchor resolution
  and placement acceptance (U7); readable headers, dimensions, the decompression-bomb limit and consistent plane
  sizes (U2, U5). The contract checks everything that can be decided from the submission itself.

## The ingestion contract

A `SlideCaseSubmission` has four parts: `slide`, `specimen`, `placement`, `assets`, and an `origin`
(`contribution` or `base`).

| Field | Rule | When violated |
|---|---|---|
| `slide.format` | one of `iso_76x26`, `us_75x25`, `petro_27x46`, `us_2x3in`, `custom` | reject |
| `slide.custom_mm` | required for `custom`; width and height 20 to 100 mm | reject |
| `slide.coverslip` | `none`, `18x18`, `22x22`, `22x40`, `22x50`, `24x50`, `24x60` or `custom` | reject |
| `slide.coverslip_custom_mm` | required for a custom coverslip; positive; must fit inside the slide in some orientation | reject |
| `slide.preparation` | one of whole mount, section, smear, squash, strew, thin section, polished section, peel, cast, fluid mount | reject |
| `slide.stain`, `slide.mountant` | at most 80 characters | reject |
| `slide.catalogue_number` | at most 64 characters | reject |
| `slide.prepared_on`, `specimen.collected_on` | `YYYY`, `YYYY-MM` or `YYYY-MM-DD`; from 1600; not in the future | reject |
| `specimen.anchor` | kind `taxon`, `rock`, `mineral`, `crystal` or `material`; a name; a taxon's reference is a GBIF usage key (digits) | reject |
| `specimen.coordinates` | latitude -90 to 90, longitude -180 to 180, uncertainty at least 0 m | reject |
| `specimen.geoprivacy` | `open`, `obscured` or `private` | reject |
| `specimen.host` | a taxon anchor | reject |
| `placement.node` | a node identifier (lowercase words joined by hyphens, levels by dots) | reject |
| `assets` | at least one | reject |
| `asset.role` | belongs to the asset's family: macro `slide_overview`, `specimen`, `place`, `label`; micro `single`, `pyramid`, `z_plane`, `polarised` | reject |
| `asset` content | exactly one of an upload id, a remote IIIF service, or (base collection) a source file | reject |
| `asset.licence` | in the licence policy for the submission's origin | reject |
| `asset.rights_holder` or `asset.creator` | at least one present | reject |
| `asset.pixel_size_um` | 0.05 to 50 micrometres per pixel | reject |
| `asset.modality` | required for micro assets; one of nine | reject |
| `asset.plane` | for `z_plane`: index at least 0, a depth, a stack name; at most 200 planes per stack | reject |
| `asset.polarisation` | for `polarised`: state `ppl` or `xpl` matching the modality, angle 0 to 360 degrees | reject |
| `asset.source` | for base-collection assets: URL, record id, retrieval date (not in the future) and a 64-hex SHA-256 | reject |
| micro asset without pixel size | | accept, flag `not_to_scale` |
| EXIF GPS on a photo while geoprivacy is private | | accept, flag `gps_stripped` (the GPS is removed before storage) |
| EXIF date more than a day from a full collection date | | accept, flag `exif_date_mismatch` |

A rejection answers HTTP 422 with `{"errors": [{"field": "slide.custom_mm.w_mm", "message": ..., "expected":
"20 to 100 mm"}]}`. Acceptance answers 200 with `{"valid": true, "flags": [...]}`.

## The licence policy

Licences are stored as canonical URIs: `https`, the `creativecommons.org` or `rightsstatements.org` host, a
trailing slash, jurisdiction ports kept (`/licenses/by-sa/3.0/de/`). Equivalent spellings (http, no slash,
`legalcode`, `deed.en`) normalise to the canonical form.

| Set | Accepted |
|---|---|
| base collection | CC0 1.0, Public Domain Mark 1.0, No Known Copyright (NKC 1.0), CC BY and CC BY-SA 2.0, 2.5, 3.0, 4.0 including jurisdiction ports |
| contributions | the base set plus CC BY-NC 4.0 and CC BY-NC-SA 4.0 |

## The catalog record and geoprivacy

The record carries identity (short id, permalink, the uppercase QR payload), the slide's physical format and
coverslip in millimetres, the label fields, the anchor, the place, the placement, the quality checks, and the
assets with their media, scale, modality, planes, polarisation, licence and source.

Geoprivacy is applied when the record is built:

- `open`: the stored point.
- `obscured`: the 0.2 degree cell that contains the stored point, and a public point inside it. For a stored point
  $(\varphi, \lambda)$ the cell is $[\varphi_0, \varphi_0 + 0.2) \times [\lambda_0, \lambda_0 + 0.2)$ with
  $\varphi_0 = 0.2\lfloor \varphi / 0.2 \rfloor$ and $\lambda_0 = 0.2 \lfloor \lambda / 0.2 \rfloor$, and the public
  point is $(\varphi_0 + 0.2u, \lambda_0 + 0.2v)$ where $u, v \in [0, 1)$ come from the SHA-256 of the slide's short
  id. The point is inside the cell, independent of the true position within it, and the same on every request.
  Latitudes are clamped to $[-90, 90]$.
- `private`: no point and no cell.

## The database

`slide` holds the case (format, label, anchor, host, place, placement, origin, status, timestamps) and `asset` holds
each image (family, role, media kind, dimensions, scale, modality, stack and plane, polarisation, licence, rights,
source, storage key, checksum, status). Every connection sets `journal_mode=WAL`, `busy_timeout=5000` and
`foreign_keys=ON`. The schema is created only by Alembic migrations; a test upgrades an empty database to the head
and compares it with the models.

Short ids use Crockford's base-32 alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ`, no I, L, O, U), eight characters,
40 bits. Resolution upper-cases the input, reads `I` and `L` as `1` and `O` as `0`, and drops hyphens.

## The TypeScript mirror

`scripts/export_contracts.py` writes `contracts/ingest.schema.json` and `contracts/catalog.schema.json`; a test fails
when they differ from the models. `frontend/scripts/generate-contract-types.mjs` turns them into
`frontend/src/contract/*.ts` with json-schema-to-typescript, and `check-contract-drift.mjs` fails when the committed
TypeScript differs from what the committed schemas produce. The web build (U9) imports only these types.
