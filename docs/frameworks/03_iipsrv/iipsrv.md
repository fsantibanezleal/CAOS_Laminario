# iipsrv (IIPImage server)

## What and why

iipsrv is a C++ FastCGI image server that serves tiles and regions of pyramidal TIFF (and JPEG 2000) over IIP,
DeepZoom, Zoomify and the IIIF Image API versions 1 to 3, at level 2 (IIPImage 1.3, May 2025,
[iipimage.sourceforge.io](https://iipimage.sourceforge.io/2025/05/iipsrv-1-3)). One pyramid file per plane needs a
tile server; iipsrv is the mature, light one (dossier 02). Cantaloupe (Java) was the heavier alternative.

## Install (exact, verified)

The official container image, pinned by digest:
`iipsrv/iipsrv@sha256:a1ce6fe828afc91893a03b41b360a50d84f905a96b410391ce4f8be636577353` (1.3, Alpine, 19 MB,
lighttpd in front of the FastCGI process). Ubuntu 24.04 ships iipsrv 1.1, which predates IIIF Image API 3.
`deploy/iipsrv/compose.yaml` runs it on loopback, with a read-only root and store, 768 MB and two CPUs.

## Usage

```bash
LAMINARIO_STORE=/srv/laminario/store docker compose -f deploy/iipsrv/compose.yaml up -d
curl http://127.0.0.1:8149/iiif/S7K2QD%2F12-3fa9.tif/info.json
curl -o tile.jpg "http://127.0.0.1:8149/iiif/S7K2QD%2F12-3fa9.tif/0,0,1024,1024/512,/0/default.jpg"
```

## Applying it here

- Tiles: nginx sends image requests to it and caches them (`deploy/nginx/laminario.conf`).
- `info.json`: the API asks it on loopback and returns the document with the public `id` and the asset's
  `rights`, which iipsrv cannot know (`app/delivery/iiif.py`).
- Gates: tiles equal to the pyramid within 2 levels at every scale factor (R-020); the container hardened (R-305).

## Caveats and licence

- It builds `id` from the request's own host, so it must be rewritten (F-020).
- It serves identifiers with `/` and with `%2F` alike.
- It reads the pyramid's resolution tags back as a IIIF physical-dimensions service.
- Read-only, the image's lighttpd needs a writable `/var/tmp`: it buffers FastCGI answers over 64 KB there, and
  without it every larger tile was cut at 64 KB. Its log directory must be owned by its user (uid 102). Both are
  tmpfs mounts in the compose file (F-019).
- GPL-3.0; run unmodified as a separate process; nothing links against it.
