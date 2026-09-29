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

Version `0.15.000`. Released, each with its wiki page:

- U0, the repository base: versioning, guards, the design document with a gate per requirement.
- U1, the data model and both contracts (ingestion and catalog), exported as JSON Schema and TypeScript ([`02_data-contracts.md`](docs/architecture/02_data-contracts.md)).
- U2, the imaging engine: scanner, TIFF and photo formats, one measured pyramid per plane, focal stacks fused as the EPFL plugin does ([`04_imaging.md`](docs/architecture/04_imaging.md)).
- U3, IIIF delivery: iipsrv behind a cached, access-checked nginx site, a IIIF Presentation 3 manifest per slide ([`05_delivery.md`](docs/architecture/05_delivery.md)).
- U4, the processing worker over a durable queue, with its journal and live events ([`06_worker.md`](docs/architecture/06_worker.md)).
- U5, resumable uploads of any size through tus, verified before they are processed ([`08_uploads.md`](docs/architecture/08_uploads.md)).
- U6, invitation-only accounts with roles ([`07_accounts.md`](docs/architecture/07_accounts.md)).
- U7, the collection tree: 3 realms, 18 collections, 130 sub-collections and groups, anchors and placement, 186 icons ([`09_collections.md`](docs/architecture/09_collections.md)).
- U8, the base collection: 505 slides from open sources, each image with its licence and provenance ([`10_base-collection.md`](docs/architecture/10_base-collection.md)).
- U9, the interface's own design system: two rooms, three faces, 18 collection hues checked for contrast ([`11_interface.md`](docs/architecture/11_interface.md)).
- U10, Explore: the realms, cabinets and drawers, search, faceted filters and the map ([`12_explore.md`](docs/architecture/12_explore.md)).
- U11, the slide as an object with its printable label and QR, and the stage with objectives, scale bar, planes, polarisers and annotations ([`13_slide.md`](docs/architecture/13_slide.md)).
- U12, Contribute: the account places, the slide case, uploads, the location of photographs, calibration ([`14_contribute.md`](docs/architecture/14_contribute.md)).
- U13, Identify: identifications, the community's agreement rule, badges, moderation ([`15_identify.md`](docs/architecture/15_identify.md)).
- U14, the profile cabinet and printable label sheets on real label stocks ([`16_cabinet.md`](docs/architecture/16_cabinet.md)).
- U15, About the collection: sources, licences, citing, how the imaging works ([`17_about.md`](docs/architecture/17_about.md)).

The units that follow are listed in the design document.

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
