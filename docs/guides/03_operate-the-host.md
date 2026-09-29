# Operate the host

Laminario runs at `https://laminario.ml.fasl-work.com` on one Hetzner Cloud VPS (4 vCPU, 8 GB, Ubuntu 24.04), with its
data on a 100 GB volume mounted at `/srv/laminario`. This guide is for whoever deploys and keeps it running. The
design of each part is in the wiki: delivery ([05](../architecture/05_delivery.md)), the worker
([06](../architecture/06_worker.md)), accounts ([07](../architecture/07_accounts.md)), uploads
([08](../architecture/08_uploads.md)), the base collection ([10](../architecture/10_base-collection.md)) and the
deployment itself ([18](../architecture/18_deployment.md)).

## What runs

| Part | How | Where |
|---|---|---|
| The API | `fasl-laminario.service` (uvicorn), as the `laminario` account | `127.0.0.1:8147` |
| The worker | `fasl-laminario-worker.service` (`python -m app.worker`), nice 10 | the job queue in the database |
| tusd | `deploy/tusd/compose.yaml`, the pinned v2.10.1 image, host network | `127.0.0.1:8148` |
| iipsrv | `deploy/iipsrv/compose.yaml`, the pinned 1.3 image, the store read-only | `127.0.0.1:8149` |
| nginx | `deploy/nginx/laminario.conf`: TLS, the web app, the IIIF tile cache with its access check, `/files/` to tusd, `/api/` to the API, the basemap | ports 80 and 443 |

## The data root

| Path | What |
|---|---|
| `/srv/laminario/laminario.sqlite3` | the database (WAL mode) |
| `/srv/laminario/store/` | pyramids and plain images by storage key, read by iipsrv |
| `/srv/laminario/sources/` | the verified originals processing reads |
| `/srv/laminario/quarantine/` | uploads until they are verified |
| `/srv/laminario/cache/` | nginx's tile and access caches (owned by `www-data`) |
| `/srv/laminario/basemap/` | the world basemap extract |
| `/srv/laminario/bake/` | base-collection bakes waiting to be imported |

## First installation

1. Settings: write `/etc/fasl-laminario.env` from `deploy/fasl-laminario.env.example`, with the secret key from the
   vault.
2. As root: `bash deploy/install.sh v0.16.000` (from a clone, or `curl` the script from the tag). It creates the
   `laminario` account and the folders, puts the code at the tag with its environment and web build, migrates the
   database, obtains the certificate and installs the nginx site.
3. As root, once: `bash /opt/fasl-apps/CAOS_Laminario/deploy/register-services.sh`. It registers and starts the API
   and the worker, and starts tusd and iipsrv. This step is a person's: services that outlive a session are not
   registered by automated runs.
4. The basemap: copy the verified extract (`scripts/fetch_basemap.py` makes it) to `/srv/laminario/basemap/`.
5. The base collection: copy the bake root to `/srv/laminario/bake/` and import it as the service account:

   ```bash
   set -a; . /etc/fasl-laminario.env; set +a
   cd /opt/fasl-apps/CAOS_Laminario
   runuser -u laminario --preserve-environment -- .venv/bin/python -m app.base import --bake /srv/laminario/bake/<bake>
   ```

   The import verifies every file against the bake's manifest and refuses a bake with a failed job before writing
   anything; a second import adds nothing.
6. The first administrator: `python -m app.accounts invite --role admin` (same environment) prints a single-use link.

## Updating

`bash deploy/install.sh <tag>` on the host: the code at the tag, its environment and build, the migrations, the site,
and a restart of the registered services. The worker returns a running job to the queue when it stops.

## Checking it

- `curl -s https://laminario.ml.fasl-work.com/api/health` names the product and the version.
- The browser gates run against the live site with `LAMINARIO_GATE_ORIGIN=https://laminario.ml.fasl-work.com`:
  `fit`, `walk`, `motion`, `states`, `qr`, `scalebar`, `stage`, `about` and `links` (`npm run gate:<name>` in
  `frontend/`). The gates that create accounts and slides (`contribute`, `identify`, `cabinet`) run only in their own
  sandbox, never against the live site.
- `journalctl -u fasl-laminario -u fasl-laminario-worker --since today` for the services; `docker logs` for tusd
  and iipsrv.

## Space

The volume holds the store, the originals, the quarantine and the caches. Whole-slide uploads are refused above 90
percent of the volume in use (the settings' `wsi_block_fraction`); the tile cache is capped at 10 GB. The volume grows
in place from the Hetzner console.
