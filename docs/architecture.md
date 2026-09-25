# Architecture

How Laminario is put together. Each page covers one part in depth.

| Page | Covers |
|---|---|
| [01 System overview](architecture/01_overview.md) | The processes on the server, what each one does, the offline lane, where data lives. |
| [02 The two data contracts](architecture/02_data-contracts.md) | The ingestion contract (what a submission must satisfy, the licence policy, the flags), the catalog contract (what the web reads, geoprivacy, quality checks), and the committed schemas with their TypeScript mirror. |
| [03 The database](architecture/03_database.md) | SQLite in write-ahead-log mode, the tables, migrations, short ids. |

Pages for the imaging engine, IIIF delivery, the worker, uploads and accounts are added by the units that build
them.
