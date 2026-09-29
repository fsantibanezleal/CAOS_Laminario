# nginx

## What and why

nginx fronts every product on the production host. For Laminario it does three jobs no application process
should: it caches tiles on disk, it checks access for each tile with a sub-request before serving it, and it
terminates TLS.

## Install (exact, verified)

The host's `nginx` 1.24.0 (Ubuntu 24.04), built `--with-http_auth_request_module`. The gate runs the same version
from the official image, pinned: `nginx@sha256:77e5d4a6ad906c5d3793764085706577fa705b1dc6f244ea0241c4b5e2155385`
(1.24.0-alpine).

## Usage

```nginx
location ~ ^/iiif/(?<iiif_key>[A-Za-z0-9._/-]+)/[^/]+/[^/]+/[^/]+/[^/]+\.(?:jpg|png|webp|tif)$ {
    auth_request /_laminario/iiif-access;      # 204 serves, 403 refuses; cached 60 s
    proxy_pass http://laminario_iipsrv;
    proxy_cache laminario_tiles;               # 30 days, 10 GB, on the data volume
}
```

## Applying it here

`deploy/nginx/laminario.conf`: tiles from iipsrv through the cache after the access check; `info.json`,
manifests and the rest of the API behind it; the access check's own path refused from outside (R-301).

## Caveats and licence

- nginx matches locations on the decoded URI, where an identifier's `%2F` are slashes again; the storage key is
  therefore everything before the last four segments.
- `auth_request` reads only 401 and 403 as a refusal; any other status is an error (500), so the API answers 403.
- Containers on a user-defined bridge network could not reach services bound to the gateway on the production host;
  the gate runs nginx with host networking, which is also the production topology.
- BSD-2-Clause.
