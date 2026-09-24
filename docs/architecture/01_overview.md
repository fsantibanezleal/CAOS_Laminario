# 01 · System overview

![Laminario system overview: a browser, nginx, the API, iipsrv, tusd, the worker, the data volume and the offline lane](svg/system-overview.svg)

## The problem the shape answers

A microscope slide scanned at 40x is billions of pixels. A contributor's file can be several gigabytes; a museum
scan can carry 80 focal planes. Such an image cannot be sent to a browser whole, so it is cut into a
multi-resolution pyramid and read tile by tile, at the zoom and place the viewer is looking at. That is why
Laminario is a server application with a processing worker, and not a static site.

## The processes

| Process | Role | Why it is separate |
|---|---|---|
| **nginx** | Terminates TLS, serves the built web app, routes `/api` to the API, `/iiif` to the tile server (behind a cache) and `/files` to the upload server. | One public entry point; everything else listens on the loopback interface only. |
| **API** (FastAPI) | The catalog of slides, the collection tree, accounts and roles, identifications, IIIF Presentation manifests, and the event stream of processing jobs. | The only process that writes the catalog. |
| **Worker** | Takes processing jobs from the database: reads scanner formats through OpenSlide, writes one pyramidal BigTIFF per image plane with libvips, builds the focus composite of z-stacks, the thumbnails, the label and its QR. | Pyramiding a 1.5-gigapixel slide takes about half a minute of CPU; that must never happen inside a web request. It runs one heavy job at a time and survives restarts: a job interrupted by a restart is queued again. |
| **iipsrv** | Serves image tiles and regions over the IIIF Image API 3, at level 2, from the pyramidal files. | A mature tile server written in C++; one file per plane instead of thousands of tile files. |
| **tusd** | Receives uploads with the tus resumable protocol, so a multi-gigabyte file survives a dropped connection. | Upload handling, retries and partial files are its whole job; it hands each finished upload to the API through a hook. |

## Where data lives

On the server everything the product stores is on a dedicated data volume mounted at `/srv/laminario`:

| Path | Holds |
|---|---|
| `store/` | the pyramidal image files, one per plane and modality |
| `quarantine/` | uploads that have not yet passed their checks |
| `cache/` | the tile cache in front of iipsrv |
| `laminario.sqlite3` | the catalog, the users, the identifications and the job journal |

Locally the same layout lives under `.data/` in the repository, which git ignores. No slide, pyramid or
database file is ever committed: a guard (`scripts/check_repo_hygiene.py`) fails the build if one is.

## The offline lane

The base collection, the openly licensed slides Laminario ships with, is curated on the owner's machine: open
sources are read, licences recorded per asset, and the result is a locked list. That list is processed by the same
pipeline as a contributor's upload, then the verified result is copied to the server. Deployment never
recomputes it.

## What arrives when

This page describes the whole system. Its parts are built in units, each with its feature design under
[`design/features/`](../design/features/); the [design document](../design/SDD.md) lists them.
