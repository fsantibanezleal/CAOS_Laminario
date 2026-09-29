# Laminario

[![CI](https://img.shields.io/github/actions/workflow/status/fsantibanezleal/CAOS_Laminario/ci.yaml?branch=develop&label=CI)](https://github.com/fsantibanezleal/CAOS_Laminario/actions)
[![License](https://img.shields.io/github/license/fsantibanezleal/CAOS_Laminario)](LICENSE)
[![Version](https://img.shields.io/github/v/tag/fsantibanezleal/CAOS_Laminario?label=version&sort=semver)](https://github.com/fsantibanezleal/CAOS_Laminario/tags)

Live: not deployed yet. It will be served at `https://laminario.ml.fasl-work.com`.

**An open collection of microscope slides, in the spirit of iNaturalist.** Every case is a real slide, shown as the
glass object it is: its format and size, the specimen seen through the coverslip, and a label with a QR code that
opens the slide's page. Behind the glass is the micro imagery, from a single photomicrograph to a whole-slide scan
with focal planes, explored in deep zoom.

## Why

Microscope slides are among the most numerous objects in natural-history and teaching collections; the Natural
History Museum in London alone holds about 2.5 million. A growing share is digitised and openly licensed, but it is
published as records in museum portals or as files in data deposits. Nobody can browse slides as slides, across
plants, animals, microbes, rocks, minerals and crystals, or add their own. Laminario is built to do both.

## What it will do

- **Explore** 18 collections in three realms (life, earth, matter) and 129 sub-collections, each with its own
  designed icon, down to the slide.
- **Look at a slide** as an object (format, macro image, label, QR), then put it on the stage: deep zoom over the
  IIIF standard, a scale bar in real units, focal planes, polarised pairs for rocks and minerals.
- **Contribute** (invited contributors): add a slide with macro photos and micro images or whole-slide scanner files
  (NDPI, SVS, MRXS, DICOM and others), uploaded resumably.
- **Identify**: the community agrees on what a slide shows, with a two-thirds agreement rule.
- **Know where every image comes from**: source, author and licence per asset, a base collection of at least 300
  openly licensed slides, and a IIIF manifest per slide for use in any IIIF viewer.

The design is in [`docs/design/SDD.md`](docs/design/SDD.md), written before any code.

## Status

Version `0.07.000`: the repository base (U0), the data model with both contracts (U1), the imaging engine (U2),
IIIF delivery (U3), the processing worker (U4), resumable uploads (U5), accounts (U6) and the collection tree (U7). The engine reads scanner,
TIFF and photo formats, writes one measured pyramid per plane and fuses focal stacks exactly as the EPFL
extended-depth-of-field plugin does ([`04_imaging.md`](docs/architecture/04_imaging.md)); iipsrv serves the
pyramids over the IIIF Image API behind a cached, access-checked nginx site, and every slide is a IIIF
Presentation 3 manifest ([`05_delivery.md`](docs/architecture/05_delivery.md)); a separate worker runs processing
jobs from a durable queue ([`06_worker.md`](docs/architecture/06_worker.md)); invited contributors have accounts
with roles ([`07_accounts.md`](docs/architecture/07_accounts.md)) and upload files of any size through tus, verified
before they are processed ([`08_uploads.md`](docs/architecture/08_uploads.md)); every slide is anchored to a real
classification and placed in a tree of 3 realms, 18 collections and 130 sub-collections and groups, each with its
own hand-drawn icon ([`09_collections.md`](docs/architecture/09_collections.md)). The units that follow are listed
in the design document.

## Architecture at a glance

![System overview](docs/architecture/svg/system-overview.svg)

A FastAPI API over SQLite, a separate processing worker (libvips with OpenSlide, one pyramidal BigTIFF per image
plane), iipsrv serving IIIF Image API 3, tusd for resumable uploads, nginx in front, and a React web app with
OpenSeadragon. Details: [`docs/architecture/01_overview.md`](docs/architecture/01_overview.md).

## Run it locally

```powershell
.\scripts\local\00_install-prereqs.ps1
.\scripts\local\01_init.ps1
.\scripts\local\03_dev.ps1        # http://127.0.0.1:8147/api/health
```

Bash equivalents sit next to each script. Full guide: [`docs/guides/01_run-locally.md`](docs/guides/01_run-locally.md).

## Tests and guards

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The test suite runs locally before every push. Continuous integration runs the lint and the guards: repository
hygiene, template residue, content standards, CI budget and the design-document gate
([`scripts/local/README.md`](scripts/local/README.md)).

## Project structure

```
app/            the server: contracts, database, services, routes (and, from U4, the processing worker)
contracts/      the committed JSON Schemas of the ingestion and catalog contracts
docs/           the wiki: design, architecture, guides
frontend/       the web app (React, Vite, TypeScript) and the generated contract types
scripts/        guards, the contract exporter, and scripts/local/ for setup and running
tests/          the test suite (local)
```

## Licence

Code: MIT ([`LICENSE`](LICENSE)). Authored documentation, icons and figures: CC BY 4.0. Every collection image keeps
the licence of its source, recorded with the image.

Maintained by Felipe Santibanez-Leal. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md).
