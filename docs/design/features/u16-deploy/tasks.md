# U16 · The deployment · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | The host chosen and measured (`hetzner-ml-fasl-work`: 4 vCPU, 8 GB, a 100 GB volume at `/srv/laminario`); the address in DNS; the port ledger rows 8147 to 8149 | R-1601, R-1602 | done |
| 2 | `deploy/install.sh`: the account, the data root's folders, the code at a ref, its environment, the web build, the migrations as the service account, the certificate, the nginx site (unlinked again if `nginx -t` fails), a restart of registered services | R-1601, R-1605, R-1606 | done |
| 3 | `deploy/register-services.sh` with the two systemd units and the tusd and iipsrv containers on loopback, memory-capped, the system read-only to them | R-1602, R-1606 | done; run on the host on 2026-09-29 at 21:30 UTC, the four services answering |
| 4 | The nginx site: HTTPS only, HSTS, the IIIF tile cache behind `auth_request`, the basemap by byte ranges, the internal routes closed, the web app's caching | R-1601, R-1602, R-1604, R-1605 | done |
| 5 | The base collection's final bake: the countries and credits of U8 and U15 brought in as records (the pixels fingerprint), the focal stacks fused in parallel processes with a stall watchdog, then the copy and the import | R-1603 | in progress |
| 6 | The gates against the live site (`LAMINARIO_GATE_ORIGIN`) and `gates/production.mjs`, which reports every requirement even when a service does not answer | R-080, R-084, R-085, R-086, R-1601 to R-1606 | done; the full run waits for the imported collection |
| 7 | Wiki page 18 with its diagram, the guide Operate the host, the U16 design and requirements | (documentation standards) | done |

## Measured on the live site (2026-09-29, before the services are registered)

`LAMINARIO_GATE_ORIGIN=https://laminario.ml.fasl-work.com node gates/production.mjs`: 13 checks pass, 5 fail, all 5
because the API is not running yet (nginx answers 502 for `/api/`).

| Requirement | Result |
|---|---|
| R-1601 HTTPS only | pass: plain HTTP answers 301 to the same path over HTTPS; the certificate is trusted, names the host and has 90 days left; HSTS `max-age=31536000` |
| R-1602 loopback only | pass: 8147, 8148 and 8149 are closed from outside; `/api/_internal/iiif-access/x` and `/api/_internal/tus-hook` answer 404 |
| R-1603 the base collection | waits for the services and the import |
| R-1604 the tile cache | waits for the services (a tile of an unknown image answers 500 while the API that authorises it is down; 403 is required) |
| R-1605 the web app's caching | pass: the index `no-cache`; a hashed asset `max-age=31536000`; `/c/insects`, `/about` and `/s/ZZZZZZZZ` answer 200 with the app |
| R-1606 reproducible | the install ran to the end on the host at the branch's head; the version check waits for the API |
