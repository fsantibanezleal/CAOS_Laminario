# U3 · IIIF delivery · design

Theory, request flows and measurements are in the wiki page
[05 IIIF delivery](../../../architecture/05_delivery.md); this page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| The IIIF Image API routes: `info.json`, image requests passed to iipsrv, the base-URI redirect | `app/routers/iiif.py`, `app/delivery/iiif.py` |
| The access check nginx asks before every tile | `GET /api/_internal/iiif-access/{key}` in the same router |
| IIIF Presentation 3 manifests | `app/delivery/manifest.py`, `GET /api/slides/{id}/manifest` |
| The remote-asset contract and the link check | `app/delivery/remote.py`, `scripts/check_remote_iiif.py` |
| The tile server, pinned | `deploy/iipsrv/compose.yaml` |
| The production site: tile cache, access check, API | `deploy/nginx/laminario.conf` |
| The IIIF version of a remote service | `asset.remote_iiif_version` (migration 0002), `media.iiif_version` in the catalog |

## Decisions

- **iipsrv 1.3 from the official image, pinned by digest**
  (`sha256:a1ce6fe8...`, 19 MB, Alpine, lighttpd in front of the FastCGI process). Ubuntu 24.04 ships
  iipsrv 1.1, which predates IIIF Image API 3 (dossier 02). The container mounts the slide store read-only,
  runs with a read-only root file system, listens on loopback only, and is limited to 768 MB and two CPUs.
- **Who writes `rights`: the API, not nginx.** The design document said nginx would rewrite `rights` from the
  asset licence. nginx cannot know a licence without a generated map that must be rebuilt and reloaded on every
  change; the API reads the licence from the same row the catalog does, so there is one source. The API also
  replaces `id`, which iipsrv builds from the request's own host (`http://127.0.0.1:8190/iiif/...` in the probe).
  R-021 is reworded accordingly.
- **Identifiers.** A IIIF identifier is the storage key as one percent-encoded path segment. nginx and Starlette
  both decode `%2F` before routing, so every route takes the whole path and reads it from the end (the
  `info.json`, the four image-request parameters, or the base URI). iipsrv accepts both forms (probed). Storage
  keys are limited to letters, digits, `.`, `-`, `_` and `/`, with no `.` or `..` segment, so no key can leave
  the store.
- **Tiles bypass the API but not the access check.** nginx sends image requests straight to iipsrv and caches
  them on the data volume for 30 days (10 GB at most). Before serving one, from the cache or not, it asks the
  API whether the key belongs to a ready pyramid of a published slide (`auth_request`, answer cached 60 s), so
  a draft or a withdrawn image stops being served within a minute. The API answers 204 or 403 (nginx reads
  any other status as an error) and nginx refuses the path from outside.
- **A cached tile never goes stale** because a storage key names one processed file and is never reused: the
  worker (U4) writes each result under a new key with a random suffix.
- **Manifests are built from the catalog record**, never from rows and never with a network call, so the
  geoprivacy rule of U1 applies to them unchanged. Each Canvas carries its own `rights` and
  `requiredStatement`; the Manifest carries `rights` only when every image agrees.
- **IIIF `rights` in `http` form.** The IIIF specifications take Creative Commons and RightsStatements.org URIs
  as `http`, and the validator's schema refuses `https`; `licences.iiif_rights` converts the canonical form.
- **The schema is pinned, not copied.** The IIIF validator's repository states no licence, so its Presentation 3
  schema is fetched at a fixed commit (`455c3c32`) and checked against its git blob hash (`c1bdef77`) into the
  data vault or the test cache. Nothing unlicensed enters this repository (finding F-018).
- **Remote services record their version.** A manifest names a remote service as `ImageService2` or
  `ImageService3`; that must be known without a network call, so the importer stores it (migration 0002).
- **Gates that need containers run where containers run.** The tile and nginx gates start the pinned images
  themselves and stop them at the end; on a machine without a container engine they are skipped with the
  reason, and the verdict records the run on the production host.
- **R-012 gained a step.** A texture close to pure noise measured 37.5 dB at Q90; the writer now also tries Q95
  (43.3 dB on that image) and records the PSNR when even that falls short.

## Interfaces owed by later units

- U4 (worker): storage keys `{short id}/{asset id}-{random}.tif`; width, height and status set when ready; the
  measured PSNR recorded.
- U7 (collection tree): `GET /api/collections/{node}/iiif`, the IIIF Collection each manifest's `partOf` names.
- U8 (base collection): every remote asset imported through `check_remote_asset`, storing version, dimensions
  and licence.
- U11 (viewer): OpenSeadragon reads `info.json`; iipsrv adds a physical-dimensions service when the pyramid has
  resolution tags, which the scale bar can use.
- U16 (deploy): the compose file and the nginx site installed, TLS added, `/srv/laminario/cache/tiles` and
  `/srv/laminario/cache/access` created for nginx.
