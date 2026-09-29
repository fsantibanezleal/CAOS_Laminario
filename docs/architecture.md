# Architecture

How Laminario is put together. Each page covers one part in depth.

| Page | Covers |
|---|---|
| [01 System overview](architecture/01_overview.md) | The processes on the server, what each one does, the offline lane, where data lives. |
| [02 The two data contracts](architecture/02_data-contracts.md) | The ingestion contract (what a submission must satisfy, the licence policy, the flags), the catalog contract (what the web reads, geoprivacy, quality checks), and the committed schemas with their TypeScript mirror. |
| [03 The database](architecture/03_database.md) | SQLite in write-ahead-log mode, the tables, migrations, short ids. |
| [04 The imaging engine](architecture/04_imaging.md) | Reading scanner, TIFF and photo formats; the limits; one measured pyramid per plane; the z-plane policy; extended depth of field (variance selection and complex wavelet fusion, exact against the EPFL plugin, with a defect of the plugin measured and corrected); derivatives without EXIF. |
| [05 IIIF delivery](architecture/05_delivery.md) | iipsrv behind nginx with a tile cache and an access check; info.json with each asset's rights; identifiers; IIIF Presentation 3 manifests with places by geoprivacy; the remote-asset contract and the link check. |
| [06 The processing worker](architecture/06_worker.md) | The durable job queue and journal in SQLite, the worker process and its one-process pool with killing timeouts, crash recovery, the Server-Sent Events stream, the processing jobs and content-addressed storage keys. |

Pages for uploads and accounts are added by the units that build them.
