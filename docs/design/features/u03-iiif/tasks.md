# U3 · IIIF delivery · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Probe the pinned iipsrv image on the production host: routing, identifiers with slashes, info.json, formats, physical dimensions | (research for the design) | done |
| 2 | `info.json` from the API with the public id and the asset's rights; image requests passed to iipsrv; the base-URI redirect; identifiers read from the end of the path | R-021 | done |
| 3 | The access check for nginx; the nginx site with the tile cache and `auth_request` | R-301 | done |
| 4 | The tile server's compose file: pinned digest, loopback, read-only root and store, tmpfs for lighttpd, limits | R-020, R-305 | done |
| 5 | Manifests: canvases, per-canvas rights and attribution, services, places by geoprivacy, links | R-022, R-302, R-303 | done |
| 6 | The remote-asset contract, the IIIF version recorded (migration 0002), the link-check command | R-023, R-304 | done |
| 7 | Gates with the pinned containers, run on the production host; the pinned IIIF schema fetched and hash-checked | R-020, R-301, R-305 | done |
| 8 | The JPEG ladder's Q95 step | R-012 (U2) | done |
| 9 | Wiki page 05 with its diagram (checked in both themes); design; guide section; version 0.03.000 | (documentation and versioning standards) | done |

## Convergence verdict (2026-09-29, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-020 tiles equal the pyramid | `tests/delivery/test_iiif_tiles.py::test_tile_equals_crop` (13 tiles over 4 levels, PNG, through the production compose file) | pass on the production host |
| R-021 rights and id per asset | `tests/delivery/test_iiif_tiles.py::test_rights_rewritten_per_asset` | pass (both machines) |
| R-022 manifests validate | `tests/delivery/test_manifest.py::test_manifest_validates` (with negative controls) | pass (both machines) |
| R-023 remote-asset contract | `tests/delivery/test_remote_iiif.py::test_remote_asset_contract` (14 cases) | pass (both machines) |
| R-301 nginx cache and access | `tests/delivery/test_iiif_tiles.py::test_nginx_caches_tiles_and_refuses_unpublished` | pass on the production host (MISS then HIT, draft 403, check hidden) |
| R-302 places by geoprivacy | `tests/delivery/test_manifest.py::test_private_place_leaves_no_trace` | pass |
| R-303 remote service version | `tests/delivery/test_manifest.py::test_remote_service_and_obscured_place` | pass |
| R-304 accepted services reported | `tests/delivery/test_remote_iiif.py::test_accepted_services_report_version_and_licence` | pass |
| R-305 tile server hardened | `tests/delivery/test_iiif_tiles.py::test_tile_server_is_read_only_on_loopback` | pass on the production host |
| R-012 ladder to Q95 | `tests/imaging/test_pyramid.py::test_quality_ladder_reaches_the_floor_on_noise` | pass (both machines) |

The full suite ran on the production host (Ubuntu 24.04, libvips 8.15.1 with OpenSlide, Docker 29.7.1) with the
fixtures, and on the development machine (Windows, libvips 8.18.6) where the four container gates are skipped
for want of a container engine; the counts are in the pull request. The Ubuntu run also closes U2's R-203 on
Ubuntu: every reader, pyramid and EDF gate passes on the distribution's libvips.

Found by running the production artifact, and fixed before release: the read-only iipsrv container cut every
tile larger than 64 KB (lighttpd buffers FastCGI answers in `/var/tmp`) and could not open its log (root-owned
tmpfs); both are now tmpfs mounts sized and owned for it.

Unmet: none. Owed by later units: storage keys with a random suffix (U4), the IIIF Collection per node (U7),
remote assets imported through the contract (U8), the scale bar from the physical-dimensions service (U11), the
site installed with TLS and its cache folders (U16).
