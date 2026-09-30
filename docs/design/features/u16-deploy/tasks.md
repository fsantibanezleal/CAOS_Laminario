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

## Convergence verdict (2026-09-30, against the live site)

The services were registered on 2026-09-29 at 21:30 UTC; the final bake (505 slides, 767 jobs, 0 failed; 69 countries;
no credit with page furniture; 10 stacks fused; no image of one colour) was copied to the volume and imported: 505
slides, 770 files hard-linked into the store and 13 copied, and `python -m app.base verify` found the 783 files of the
manifest in the served store with their SHA-256 and size. Three images of one slide (the re-baked Colorados stack's
two composites and height map) were still uploading and were imported after, with the full manifest.

| Requirement | Gate | Result |
|---|---|---|
| R-1601 HTTPS only | `frontend/gates/production.mjs` | pass: plain HTTP answers 301 to the same path over HTTPS; the certificate is trusted, names the host and has 89 days left; HSTS `max-age=31536000` |
| R-1602 loopback only | `frontend/gates/production.mjs` | pass: 8147, 8148 and 8149 closed from outside; the internal routes answer 404 |
| R-1603 the base collection | `frontend/gates/production.mjs`; `python -m app.base verify` | pass: the lock's 505 slides published, from five known sources, 14 whole-slide scans, 29 countries; every stored file equal to the manifest |
| R-1604 the tile cache | `frontend/gates/production.mjs` | pass: a tile's first request a miss, its second a hit with the same 17,653 bytes; a tile of an image no published slide holds refused (403) |
| R-1605 the web app's caching | `frontend/gates/production.mjs` | pass: the index `no-cache`, a hashed asset for a year, the app's addresses answer with the app |
| R-1606 reproducible | `frontend/gates/production.mjs` | pass: the install and the registration ran to the end; the site serves the repository's version |

The production gate passes 22 of 22. Its first run found its own defect (it read a tile service's address from the asset
instead of its media record) and it was fixed. The browser gates against the live site were not run for this release,
on Felipe's instruction; the interface they judge is replaced by U17.

Building it found what the design could not: the bake's record refresh that trusted old index entries (F-050), the
community store's checks without the asset role (F-051), a Hamamatsu plane beyond the JPEG limit read black (F-052),
a replacement pick over the engine's limits (F-053), a fusion broken by the workstation's own load (F-054), fusion
processes that outlived a killed job, and an import that would have held the images twice on the volume.
