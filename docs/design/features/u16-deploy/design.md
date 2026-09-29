# U16 · The deployment · design

How the parts fit is the wiki page [18 The deployment](../../../architecture/18_deployment.md); the operator's steps
are the guide [Operate the host](../../guides/03_operate-the-host.md).

## What the unit delivers

| Part | Where |
|---|---|
| The API and worker units, run as the `laminario` account with the system read-only to them | `deploy/systemd/` |
| The nginx site: TLS, the web app, the tile cache and its access check, uploads, the basemap | `deploy/nginx/laminario.conf` |
| The install script (code, environment, build, migrations, certificate, site) and the registration script (the services) | `deploy/install.sh`, `deploy/register-services.sh` |
| The settings the host needs, without their values | `deploy/fasl-laminario.env.example` |
| The gates' production mode and the production gate | `frontend/gates/lib/serve.mjs`, `frontend/gates/production.mjs` |

## Decisions

- **The host is the ml box** (`hetzner-ml-fasl-work`, 4 vCPU, 8 GB) at `laminario.ml.fasl-work.com`, which the `*.ml`
  wildcard already resolves; the data root is the 100 GB volume at `/srv/laminario`, decided at planning. The ports
  8147 to 8149 were free on the live check of 2026-09-29.
- **Install and registration are two scripts.** The install is idempotent and can run on every update; it never
  registers a long-running service. Registering the API, the worker and the two containers is a person's step, once
  (`deploy/register-services.sh`), because the management rules keep services that outlive a session out of
  automated runs.
- **One process per role, as in development.** One uvicorn process for the API (the tests run one; SQLite in WAL mode
  serves its readers), the worker at nice 10 so imaging yields to requests, both with `ProtectSystem=strict` and the
  data root as their only writable path.
- **The web app from the release's own build**, served by nginx: hashed assets for a year, the rest for a day,
  `index.html` never cached, every other address answered with the app (the app routes it). Cache headers use
  `expires`, so the server's security headers reach every location.
- **The certificate first, then the site.** certbot's nginx authenticator obtains it without editing the site file,
  so the repository's file is the one installed; the package's timer renews it.
- **The base collection is imported, not re-baked.** The bake runs where the processing time is (the workstation),
  is refreshed for record-only changes without reprocessing images, is copied to the volume and imported; the import
  verifies every file against the manifest and refuses a failed bake before writing anything.
- **The gates run against the live site** with `LAMINARIO_GATE_ORIGIN`: fit, walk, motion, states, the QR, the scale
  bar, the stage, About and the links, plus a production gate for what only a deployment has (HTTPS, the redirect,
  loopback-only services, the cache, the imported collection, the version). The tile-server gates the workstation
  could not run (its Docker engine is unavailable) run here, over the base collection's own scans.
