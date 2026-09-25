# 03 · The database

One SQLite file, `laminario.sqlite3`, in the data root (`.data/` locally, `/srv/laminario` on the server),
shared by the API (asynchronous driver) and, from U4, the processing worker (synchronous driver).

## Why SQLite

One server, one writer at a time (the API writes the catalog; the worker writes job progress and asset state),
readers that must never wait on the writer, and no operations team. Write-ahead-log mode gives exactly that:
readers see the last committed state while a write is in progress. Every connection sets three pragmas:

| Pragma | Why |
|---|---|
| `journal_mode=WAL` | readers do not block the writer and the writer does not block readers |
| `busy_timeout=5000` | a second writer waits up to five seconds for the lock instead of failing at once |
| `foreign_keys=ON` | SQLite enforces foreign keys only when asked, per connection |

## Tables

Tables arrive with the units that need them; each unit adds a migration. U1 creates:

| Table | Holds |
|---|---|
| `slide` | the case: short id, status (`draft`, `processing`, `published`, `hidden`), origin, format and coverslip in millimetres, label fields, anchor and host, place and geoprivacy, placement, contributor, timestamps |
| `asset` | each image of a slide: family and role, media kind (`pyramid`, `image`, `remote_iiif`), status (`pending`, `ready`, `failed`), dimensions and pixel size, modality, stack and plane, polarisation, licence, rights, source, storage key, size and checksum |

Indexes: `slide.status`, `slide.placement_node`, `(slide.anchor_kind, slide.anchor_ref)`, `asset.slide_id`.
Deleting a slide deletes its assets (cascade).

## Migrations

The schema is created only by Alembic migrations (`app/db/migrations/`), never by `create_all`, so what runs in
production is what the tests exercise. `python -m app.db.migrate` upgrades the configured database to the head;
a test upgrades an empty database and compares every table, column, nullability and index with the models.

## Short ids

A slide's public id is eight characters of Crockford's base 32 (`0123456789ABCDEFGHJKMNPQRSTVWXYZ`: no I, L,
O or U), 40 bits, printed in upper case on the label. Reading is forgiving, as Crockford specifies: case is
ignored, `I` and `L` read as `1`, `O` as `0`, hyphens are dropped. A collision on creation draws a new id.
