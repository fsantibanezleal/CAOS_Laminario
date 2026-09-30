# 05 · IIIF delivery

![IIIF delivery: nginx in front of iipsrv with a tile cache and an access check, the API writing info.json and manifests, remote IIIF services under a contract](svg/iiif-delivery.svg)

A slide's images reach a browser through the International Image Interoperability Framework (IIIF): the Image
API for the pixels, the Presentation API for the slide as a document. Any IIIF viewer (Mirador, the Universal
Viewer) can therefore open a Laminario slide, and Laminario can show images other institutions serve the same
way.

## 1. The Image API

The IIIF Image API 3.0 addresses a region of an image as

```
{base}/iiif/{identifier}/{region}/{size}/{rotation}/{quality}.{format}
```

with an `info.json` per image that declares its size, the tile size and the scale factors a viewer can ask for.
At level 2 a server renders arbitrary regions and sizes; a deep-zoom viewer such as OpenSeadragon only asks for
tiles: region $\big(c\,t\,s,\; r\,t\,s,\; \min(t s, W - c t s),\; \min(t s, H - r t s)\big)$ at size
$\lceil w / s \rceil$ for tile column $c$, row $r$, tile size $t = 512$ and scale factor $s \in \{1, 2, 4, \ldots\}$,
which is exactly one tile of one level of the pyramid U2 writes.

**The tile server** is iipsrv 1.3 (IIPImage, GPL-3.0, run unmodified as its own process), from the official
container image pinned by digest. It reads the pyramid files of the slide store read-only and answers at level
2. Probed on the production host with a U2 pyramid:

| Question | Answer |
|---|---|
| `info.json` | IIIF 3 context, width and height, `sizes` for each level, tiles of 512 px with scale factors 1, 2, 4, 8, `maxWidth` 5000 |
| identifier with `/` or with `%2F` | both answered |
| resolution tags of the pyramid | read back as a physical-dimensions service (`physicalScale` 5e-05 cm per pixel for 0.5 um) |
| output formats | JPEG, PNG, WebP, TIFF, AVIF |
| `id` | built from the request's own host (`http://127.0.0.1:8190/...`), so it must be rewritten |

**`info.json` comes from the API.** iipsrv does not know the public address or any licence, so the API resolves
the identifier to its asset (a ready pyramid of a published slide, or 404), asks iipsrv on loopback (cached in
memory), and returns the document with `id` set to the public address and `rights` set to the asset's licence.
IIIF takes Creative Commons and RightsStatements.org URIs in their `http` form, so the canonical `https` form of
the licence policy is converted (`http://creativecommons.org/licenses/by/4.0/`).

**Identifiers.** An identifier is the storage key as one percent-encoded segment (`S7K2QD%2F12-3fa9.tif`). Web
servers decode `%2F` before they route, so both nginx and the API read the path from its end: `info.json`, or four
trailing segments that are a valid region, size, rotation and quality.format, or else the base URI (which
redirects to `info.json`, as the specification asks). Storage keys hold only letters, digits, `.`, `-`, `_` and
`/`, with no `.` or `..` segment, so none can reach outside the store.

## 2. Tiles in production

nginx sends image requests straight to iipsrv and caches the answers on the data volume, for 30 days and 10 GB
at most. A storage key names one processed file and is never reused (a reprocessed image gets a new key), so a
cached tile cannot go stale. Before any tile is served, from the cache or not, nginx asks the API whether its key
belongs to a published slide (`auth_request`); the answer, 204 or 403, is cached for 60 seconds. A draft is never
served, and a withdrawn image stops being served within a minute. The check's own path is refused from outside.

Measured by the gate (R-301) with the pinned nginx 1.24 and iipsrv images: the first request of a tile is a cache
`MISS`, the second a `HIT` with identical bytes, equal to what iipsrv returns directly; a tile of an unpublished
image answers 403 without reaching the cache.

nginx keeps up to 16 idle connections to iipsrv and to the API, and drops each after 4 seconds idle. Both backends
close an idle connection themselves (uvicorn after 5.0 s, iipsrv's lighttpd after 6.0 s, measured on the host on
2026-09-30); at nginx's default of 60 s a request written on a connection the backend was closing came back as
"upstream prematurely closed connection", and the page showed a 502 in place of a thumbnail. The gate checks that
every kept upstream stops reusing a connection before its backend closes it, and measures the pinned iipsrv's close.

**Tiles equal the pyramid** (R-020): tiles requested as PNG through the API at every scale factor (corner, edge
and middle tiles of each level) equal the same region cropped by libvips from the matching level of the pyramid,
within 2 grey levels per channel. PNG keeps the comparison free of a second JPEG encoding.

## 3. Manifests

Each published slide is a IIIF Presentation 3 Manifest at `/api/slides/{id}/manifest`, built from its catalog
record (so geoprivacy is already applied) without any network call:

- one Canvas per ready micro asset (each focal plane and each polarisation state is an asset) and per macro
  asset, micro first, in the slide's order, each painted with its image and its image service;
- `rights` and `requiredStatement` (creator or rights holder, licence, source record) on every Canvas, since the
  images of one slide can carry different licences; `rights` on the Manifest only when they all agree;
- `metadata` with the name, rank, collection, preparation, stain, mountant, dates, locality, type status,
  catalogue number, slide size, quality badge and origin;
- `homepage` (the slide's permalink), `seeAlso` (the catalog record and its JSON Schema), `partOf` (the
  collection node as a IIIF Collection), `provider`, a `thumbnail` with its service;
- `navPlace` (the IIIF extension): the point for an open place, the 0.2 degree cell for an obscured one, nothing
  for a private one, whose locality is also left out.

Every manifest validates against the IIIF validator's Presentation 3 schema (R-022). The schema is pinned by
commit and git blob hash and fetched, not copied, because its repository states no licence. The gate also shows the
validator is not vacuous: the `https` form of a licence and a Canvas without a size are both refused.

## 4. Remote IIIF services

Another institution's image can be a slide's image without copying it: the browser reads that service directly.
A remote service is accepted only when it meets the remote-asset contract (R-023): its `info.json` answers 200
with JSON; it declares IIIF Image API 2 or 3; it declares a licence (`rights` in version 3, `license` in version
2) that the policy accepts for the slide's origin; its `Access-Control-Allow-Origin` lets this deployment's
pages read it; and its dimensions equal the recorded ones. Every refusal names its field and what was expected.
The version is recorded, so the manifest declares `ImageService2` or `ImageService3` correctly.

The link check, `python scripts/check_remote_iiif.py`, re-reads every remote asset, reports any that no longer
meets the contract or whose licence changed, and changes nothing.

## 5. How it is verified

| Gate | Checks |
|---|---|
| `tests/delivery/test_iiif_tiles.py` | rights and id per asset, drafts and traversal refused, the redirect, the access check; tiles equal to the pyramid through the pinned iipsrv; nginx cache and access check through the pinned nginx; upstream idle connections dropped before the backends close them |
| `tests/delivery/test_manifest.py` | schema validity, canvases, rights per canvas, services, places by geoprivacy, drafts |
| `tests/delivery/test_remote_iiif.py` | every clause of the remote-asset contract, both API versions, unreachable hosts |

The container gates start the pinned images and stop them at the end; without a container engine they are
skipped, and the unit's verdict records the run on the production host.

## References

- IIIF Image API 3.0. [iiif.io/api/image/3.0](https://iiif.io/api/image/3.0/).
- IIIF Presentation API 3.0. [iiif.io/api/presentation/3.0](https://iiif.io/api/presentation/3.0/).
- IIIF navPlace extension. [iiif.io/api/extension/navplace](https://iiif.io/api/extension/navplace/).
- IIPImage server 1.3. [iipimage.sourceforge.io](https://iipimage.sourceforge.io/2025/05/iipsrv-1-3).
- IIIF presentation validator, schema `iiif_3_0.json` at commit `455c3c32`.
  [github.com/IIIF/presentation-validator](https://github.com/IIIF/presentation-validator).
