# 01 · Run it locally

The numbered scripts in `scripts/local/` take a fresh clone to a running API. Run them in order from the
repository root. PowerShell is shown first; every script has a bash twin with the same behaviour.

## 0. Prerequisites

```powershell
.\scripts\local\00_install-prereqs.ps1          # checks Python 3.12, Node 22 to 24, git, libvips, Docker
.\scripts\local\00_install-prereqs.ps1 -Install # installs what is missing with winget
```

It only checks unless you pass `-Install`, so it never replaces software that already works.

## 1. Set up

```powershell
.\scripts\local\01_init.ps1
```

Creates `.venv` with Python 3.12, installs `requirements-dev.txt`, and writes a local `.env`. The `.env` comes from
the file named by `LAMINARIO_ENV_SOURCE` when that variable is set, otherwise from `.env.example`. Secrets never
live in this repository.

## 2. Run the API

```powershell
.\scripts\local\03_dev.ps1              # http://127.0.0.1:8147
.\scripts\local\03_dev.ps1 -Port 8150
```

Open `http://127.0.0.1:8147/api/health`; it answers with the product name and the version from the `VERSION`
file. The interactive API documentation is at `/api/docs`. The script refuses to start on a port another
program already holds.

## 3. The database and the web app

```powershell
.\.venv\Scripts\python.exe -m app.db.migrate      # creates or upgrades .data/laminario.sqlite3
cd frontend
npm ci
npm run dev                                        # http://127.0.0.1:5909, proxies /api to the API
```

The web dev server proxies `/api`, `/iiif` and `/media` to the API on port 8147, so the app is served from one
origin as it is in production.

## 4. The imaging engine

The engine uses libvips with OpenSlide. On Windows, download `vips-dev-w64-all-<version>.zip` from the
[libvips Windows builds](https://github.com/libvips/build-win64-mxe/releases) (it includes OpenSlide), unzip it
anywhere, and point `.env` at its `bin` folder; on Ubuntu, `sudo apt install libvips42t64 libvips-tools` and leave
the variable unset.

```ini
LAMINARIO_VIPS_BIN=E:/_Tools/libvips/vips-dev-8.18/bin
LAMINARIO_FIXTURES=E:/_Datos/laminario
LAMINARIO_TEST_TMP=E:/_Temp/laminario-pytest
```

`LAMINARIO_FIXTURES` is the local data vault the imaging tests read: `samples/` (the slide files: CMU-1, the
Smithsonian ostracod NDPI, the NHM louse scan, the Commons thin section; and for the contribute gate a photograph
that carries its GPS position, `commons_san_cristobal_gps.jpg`: "Atardecer desde el cerro San Cristobal" by
Mulatoenchile, Wikimedia Commons, CC BY-SA 3.0, SHA-256 `1435f31d200aee9c653335bf78b7c6ca5ab60a433732e4ac1a957139d03bde27`) and `edf-reference/` (the EPFL
extended-depth-of-field plugin's three sample stacks, its outputs, and the runners that produced them). None of
it is in git; without it those tests are skipped and say so. Put the test folder on a scratch drive: the
pyramid tests write hundreds of megabytes.

Every measurement table of the imaging page is reproduced by

```powershell
.\.venv\Scripts\python.exe scripts\bench_imaging.py --out E:/_Temp/laminario-bench
```

which prints each table and writes `bench-imaging.json` (about ten minutes).

## 5. The tile server

Images are served by iipsrv, the IIIF tile server, from the official container image pinned by digest. With a
container engine running, start it over the local slide store:

```powershell
$env:LAMINARIO_STORE = "$PWD\.data\store"
docker compose -f deploy/iipsrv/compose.yaml up -d      # http://127.0.0.1:8149, loopback only
docker compose -f deploy/iipsrv/compose.yaml down       # when done
```

The API asks it for each image's `info.json` and, locally, passes tile requests through, so the web app uses the
same `/iiif/...` addresses as production, where nginx serves tiles directly (`deploy/nginx/laminario.conf`).
The delivery tests start their own pinned containers and stop them; without a container engine they are skipped.

Remote IIIF images are checked again, without changing anything, with

```powershell
.\.venv\Scripts\python.exe scripts\check_remote_iiif.py
```

## 6. The worker

Processing runs in its own process, next to the API:

```powershell
.\.venv\Scripts\python.exe -m app.worker                      # Ctrl+C puts a running job back in the queue
.\.venv\Scripts\python.exe -m app.jobs enqueue probe '{"steps": 3, "seconds": 2}'
.\.venv\Scripts\python.exe -m app.jobs wait <id>               # the job and its events; exit 0 when it succeeded
```

A job's progress is also at `http://127.0.0.1:8147/api/jobs/<id>/events`, as the browser receives it.

## 7. Accounts

There is no open sign-up. Create the first admin from the command line, then invite everyone else from the app:

```powershell
.\.venv\Scripts\python.exe -m app.accounts invite --role admin   # prints a one-time link, valid 7 days
```

Open the link in the web app (or `POST /api/auth/register` with its token) to create the account. Without a mail
sender in `.env`, invitation links appear once to the person who issues them. Password-reset links are signed with
`LAMINARIO_SECRET_KEY`; leave it unset locally (a random key per run) and set it in production.

## 8. Uploads

Uploads go through tusd, the tus server. Locally, download the v2.10.1 release for your system from
[github.com/tus/tusd/releases](https://github.com/tus/tusd/releases), check it against its `.sha256`, and start it
next to the API with the flags of `deploy/tusd/compose.yaml`:

```powershell
tusd.exe -host=127.0.0.1 -port=8148 -base-path=/files/ -upload-dir=.data\quarantine `
  -hooks-http=http://127.0.0.1:8147/api/_internal/tus-hook -hooks-http-forward-headers=Cookie `
  -hooks-enabled-events=pre-create,post-finish,post-terminate -disable-download -show-greeting=false
```

The worker verifies each finished upload and processes it. The upload tests start their own tusd from
`LAMINARIO_TUSD_BIN` and skip without it. The web dev server and the preview proxy `/files/` to tusd keeping the
page's host, so the addresses tusd gives the browser are the page's own, as behind nginx.

## 9. The collection tree

The tree, its vocabularies and the icons are files in the repository; the API reads them at start. Taxon anchors are
looked up on GBIF the first time a key is seen (`LAMINARIO_GBIF_API_URL`, default `https://api.gbif.org/v1`) and kept
in the database. After changing the tree or the icons:

```powershell
.\.venv\Scripts\python.exe scripts\lock_taxa.py            # resolve new taxa on GBIF (network)
.\.venv\Scripts\python.exe scripts\build_icons.py          # the sprite and the contact sheet
.\.venv\Scripts\python.exe scripts\render_tree_docs.py     # docs/collections/tree.md
.\.venv\Scripts\python.exe -m pytest tests\collections    # the guard, placement, icons, API
```

The mineral and rock vocabularies are rebuilt and checked from their sources in the data vault
(`LAMINARIO_FIXTURES\vocab`): `scripts\build_minerals.py --vault $env:LAMINARIO_FIXTURES` and
`scripts\check_rock_terms.py --vault $env:LAMINARIO_FIXTURES`; the two vault tests skip without it. The tests never call
GBIF: a local server replays recorded answers (`tests\gbif_replay.py`).

## 10. The interface

The web app is built from its token source, its font subsets and its catalogues; the generated files are committed.
After changing one of the sources:

```powershell
cd frontend
npm run tokens                      # src/design/tokens.css from src/design/tokens.json
npm run check:contrast              # every declared colour pair against its WCAG 2.2 minimum
npm run check:i18n                  # both catalogues complete
cd ..
.\.venv\Scripts\python.exe scripts\build_fonts.py   # the three faces from the pinned upstream files (cached in the vault)
```

The browser gates run against the real build in Playwright's Chromium, with the browser cache outside the repository:

```powershell
cd frontend
npm run build
$env:PLAYWRIGHT_BROWSERS_PATH = "<browser cache folder>"; npx playwright install chromium
npm run gate:fit                    # no sideways scroll: 4 widths x 2 rooms x 2 languages, with screenshots
npm run gate:motion                 # nothing moves with reduced motion
npm run gate:states                 # focus, tooltip, dialog, toast, with screenshots
```

The screenshots land in `frontend/.gates/` (ignored by git) and are read before a unit closes. The specimen place
is at `/design` in `npm run dev`.

The contribute gate runs the whole path end to end and builds its own sandbox (a fresh data root, the API, the
worker, tusd and the preview), so ports 8147, 8148 and 4909 must be free. It uploads CMU-1 and processes it, which
takes a few minutes:

```powershell
cd frontend
npm run build
$env:LAMINARIO_FIXTURES = "E:/_Datos/laminario"; $env:LAMINARIO_TUSD_BIN = "<tusd.exe>"
$env:LAMINARIO_TEST_TMP = "E:/_Temp/laminario-gates"   # where the sandbox goes; removed when the gate passes
npm run gate:contribute
```

## Tests and guards

The full test suite runs locally; continuous integration runs only the lint and the guards.

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app tests scripts
.\.venv\Scripts\python.exe scripts\check_repo_hygiene.py      # nothing that belongs outside git is tracked
.\.venv\Scripts\python.exe scripts\check_template_residue.py  # no template example survived
.\.venv\Scripts\python.exe scripts\check_content_standards.py # no em-dash, no emoji
.\.venv\Scripts\python.exe scripts\check_ci_budget.py         # CI stays cheap
.\.venv\Scripts\python.exe scripts\check_sdd.py               # every requirement names a gate that exists
.\.venv\Scripts\python.exe scripts\export_contracts.py --check # committed schemas equal the models
cd frontend
npm run contract:check                                        # committed TypeScript equals the schemas
npm run typecheck
npm test
npm run check:tokens; npm run check:contrast; npm run check:i18n
```

After a change to a contract model: `python scripts/export_contracts.py`, then `npm run contract:generate`.

Tests write only to a temporary folder: `LAMINARIO_TEST_TMP` when set, otherwise `.tmp/pytest` inside the
repository (git ignores it).
