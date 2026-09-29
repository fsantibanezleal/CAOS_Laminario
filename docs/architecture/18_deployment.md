# 18 · The deployment

![The deployment: one host behind nginx with TLS; the API and the worker as services of their own account; tusd and iipsrv from their pinned images on loopback; the data root on a 100 GB volume; the base collection baked on a workstation and imported; the gates run against the live site](svg/deployment.svg)

Laminario runs at `https://laminario.ml.fasl-work.com` on one Hetzner Cloud VPS, `hetzner-ml-fasl-work` (4 vCPU,
8 GB, Ubuntu 24.04, Helsinki), chosen at planning for its disk headroom (tile pyramids and multi-gigabyte uploads) and
because it hosts the heavier applications. The requirements are R-1601 to R-1606
([U16 requirements](../design/features/u16-deploy/requirements.md)); the decisions are in the
[U16 design](../design/features/u16-deploy/design.md); the operator's steps are the guide
[Operate the host](../guides/03_operate-the-host.md).

## 1. The processes

| Process | Runs as | Listens | Started by |
|---|---|---|---|
| nginx | `www-data` | 80, 443 | the host (shared with the other sites) |
| The API (uvicorn, one process) | `laminario` | `127.0.0.1:8147` | `fasl-laminario.service` |
| The worker (`python -m app.worker`, nice 10) | `laminario` | nothing | `fasl-laminario-worker.service` |
| tusd v2.10.1 (pinned image, host network, read-only root) | the `laminario` uid | `127.0.0.1:8148` | `deploy/tusd/compose.yaml` |
| iipsrv 1.3 (pinned image, the store read-only) | lighttpd inside | `127.0.0.1:8149` | `deploy/iipsrv/compose.yaml` |

Both units make the system read-only to the process (`ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`,
`NoNewPrivileges`) and leave `/srv/laminario` as the only writable path; memory is capped (1.5 GB for the API, 3 GB
for the worker, 256 MB for tusd, 768 MB for iipsrv) so imaging cannot starve the host's other applications.

## 2. nginx

One site, `deploy/nginx/laminario.conf`:

| Path | Goes to | Caching |
|---|---|---|
| `http://` anything | a 301 to `https://` | |
| `/iiif/{key}/{region}/{size}/{rotation}/{quality}.{format}` | iipsrv, after `auth_request` asks the API whether the key belongs to a published slide (answer cached 60 s) | 30 days on the volume, 10 GB at most; `X-Cache-Status` |
| `/iiif/...` otherwise (`info.json`, manifests) | the API | |
| `/media/{key}` | the API (a published slide's photograph or height map) | 30 days |
| `/files/` | tusd, unbuffered, no size limit (tusd enforces 30 GB) | |
| `/api/explore/basemap.pmtiles` | the file on the volume, read by byte ranges | 30 days |
| `/api/` | the API, unbuffered for server-sent events | |
| `/api/_internal/` | 404 from outside | |
| `/assets/` | the web build's hashed files | a year |
| anything else | the file, or `index.html` (the app routes the address) | a day; `index.html` never |

HSTS, `nosniff` and a referrer policy are set on the server and reach every location, since the web app's locations
set their caching with `expires` rather than their own `add_header`.

## 3. Installing, registering, updating

`deploy/install.sh <tag>` is idempotent: the `laminario` account, the folders of the data root (the caches owned by
`www-data`), the code at the tag in `/opt/fasl-apps/CAOS_Laminario`, its virtual environment from
`requirements-api.txt`, the web build, the database migrations run as the service account with the service's
settings, the certificate (certbot's nginx authenticator, which leaves the site file alone; the package's timer renews
it), the site, and a restart of the services if they are registered. `deploy/register-services.sh` registers and
starts the two units and the two containers, once (done on 2026-09-29); every later update is the install alone,
which restarts them on the new code. The settings are `/etc/fasl-laminario.env` (root:laminario, 0640), whose secret key
is kept in the management repository's vault.

## 4. The base collection on the host

The bake runs where the processing time is: the NMNH focal stacks fuse for hours each on a workstation. A bake root is
a complete data root (database, store, manifest). After the lock changes only in records (credits, countries), the
bake refreshes those records without processing images again (the pixels fingerprint, page 10 section 3.6). The root
is copied to `/srv/laminario/bake/` and imported by `python -m app.base import --bake`: every stored file is checked
against the manifest's SHA-256 and size before anything is written, a bake with a failed job is refused, and a second
import adds nothing. `python -m app.base verify --bake` then checks the served store against the same manifest, which
is how R-1603's "every stored file equal to its manifest's SHA-256" is measured on the host.

## 5. The gates against the live site

`LAMINARIO_GATE_ORIGIN=https://laminario.ml.fasl-work.com` points the browser gates at the deployment: no preview is
started and the API is read through the same origin, as a visitor reads it. fit, walk, motion, states, the QR, the
scale bar, the stage, About and the links run there; so do the tile-server checks the workstation could not run (its
Docker engine is unavailable): the tray's thumbnails, the scale bar at every objective, the planes and the polarised
pairs. `gates/production.mjs` checks what only a deployment has (R-1601 to R-1606). The gates that create accounts
and slides (contribute, identify, cabinet) run only in their own sandbox.
