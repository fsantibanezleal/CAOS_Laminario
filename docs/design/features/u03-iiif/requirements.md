# U3 · IIIF delivery · requirements

R-020 to R-023 moved here from the design document; R-021 names the API instead of nginx as the component
that writes `rights` (see the design, "Who writes rights"). R-301 to R-305 are this unit's own. R-012 of U2
gained a third quality step during this unit; its gate is listed at the end.

```
R-020  WHEN a tile is requested from the IIIF service, THE tile SHALL equal the libvips crop of the same region within 2 levels per channel after decoding.
       Gate: tests/delivery/test_iiif_tiles.py::test_tile_equals_crop

R-021  THE IIIF info.json served for an asset SHALL declare that asset's licence as rights and this deployment's public address as id.
       Gate: tests/delivery/test_iiif_tiles.py::test_rights_rewritten_per_asset

R-022  THE manifest generator SHALL produce Presentation 3 manifests that validate against the pinned JSON Schema.
       Gate: tests/delivery/test_manifest.py::test_manifest_validates

R-023  WHEN a remote IIIF asset is imported, THE importer SHALL verify availability, rights, CORS and dimensions, and SHALL reject it otherwise.
       Gate: tests/delivery/test_remote_iiif.py::test_remote_asset_contract

R-301  THE production web server SHALL serve a tile from its cache after the first request, SHALL refuse the tiles of an image that is not published before the cache is read, and SHALL NOT expose the access check.
       Gate: tests/delivery/test_iiif_tiles.py::test_nginx_caches_tiles_and_refuses_unpublished

R-302  WHEN a slide's place is private, THE manifest SHALL carry neither a place nor a locality; WHEN it is obscured, only the 0.2 degree cell.
       Gate: tests/delivery/test_manifest.py::test_private_place_leaves_no_trace

R-303  WHEN a manifest references a remote service, THE manifest SHALL declare the Image API version recorded at import.
       Gate: tests/delivery/test_manifest.py::test_remote_service_and_obscured_place

R-304  WHEN a remote service passes the contract, THE check SHALL report its Image API version, its canonical licence and its dimensions.
       Gate: tests/delivery/test_remote_iiif.py::test_accepted_services_report_version_and_licence

R-305  THE tile server's compose file SHALL run the pinned image with a read-only root, a read-only store, its port on loopback only, and its memory and CPU limits.
       Gate: tests/delivery/test_iiif_tiles.py::test_tile_server_is_read_only_on_loopback

R-012  (U2, extended) THE pyramid writer SHALL reach 38 dB mean PSNR at level 0, climbing JPEG Q85, Q90 (full chroma) and Q95, and SHALL record the measured PSNR when even Q95 falls short.
       Gate: tests/imaging/test_pyramid.py::test_quality_ladder_reaches_the_floor_on_noise
```
