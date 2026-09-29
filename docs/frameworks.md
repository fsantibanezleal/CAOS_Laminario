# Frameworks

One card per library or engine Laminario actually uses for its core work, with the exact version verified, how it
is used here, and its caveats and licence. Every one is pinned: Python packages in `requirements-api.txt`,
system libraries and container images in the deployment files. Cards are added by the unit that brings the
library in.

| Card | Role | Pinned |
|---|---|---|
| [01 libvips, through pyvips](frameworks/01_libvips/libvips.md) | reading, converting and writing images; the pyramid writer | libvips 8.18.6 (Windows), 8.15.1 (Ubuntu), pyvips 3.2.0 |
| [02 OpenSlide](frameworks/02_openslide/openslide.md) | scanner formats, levels, associated images | bundled with libvips on both machines |
| [03 iipsrv](frameworks/03_iipsrv/iipsrv.md) | the IIIF Image API tile server | 1.3, container digest `a1ce6fe8...` |
| [04 pebble](frameworks/04_pebble/pebble.md) | the worker's process pool with killing timeouts | 5.2.2 |
| [05 tifffile](frameworks/05_tifffile/tifffile.md) | vendor TIFF tags, ImageJ stacks, in-place tag edits | 2026.9.20 |
| [06 nginx](frameworks/06_nginx/nginx.md) | tile cache, per-tile access check, TLS | 1.24.0 (host; gate image digest `77e5d4a6...`) |
| [07 EPFL Extended Depth of Field](frameworks/07_epfl-edf/epfl-edf.md) | the reference implementation the EDF port is measured against (not run by the product) | the plugin's jar, run unmodified |
| [08 fastapi-users](frameworks/08_fastapi-users/fastapi-users.md) | accounts, database sessions in a cookie, password reset | 15.0.5, with fastapi-users-db-sqlalchemy 7.0.0 |
| [09 tusd](frameworks/09_tusd/tusd.md) | resumable uploads (tus 1.0) with hooks into the API | 2.10.1, image digest `7b1c552a...` |
| [10 GBIF species API](frameworks/10_gbif-api/gbif-api.md) | taxon anchors: the backbone's keys, lineages and names | API v1, backbone `d7dddbf4...`, 134 taxa locked |

Libraries that are ordinary application plumbing (FastAPI, Pydantic, SQLAlchemy, Alembic, NumPy, SciPy, PyYAML for
the tree, pypdf for building the mineral and rock vocabularies) are pinned
in the requirements files and documented where they matter, in the architecture pages.
