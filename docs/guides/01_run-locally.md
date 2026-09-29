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
Smithsonian ostracod NDPI, the NHM louse scan, the Commons thin section) and `edf-reference/` (the EPFL
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
```

After a change to a contract model: `python scripts/export_contracts.py`, then `npm run contract:generate`.

Tests write only to a temporary folder: `LAMINARIO_TEST_TMP` when set, otherwise `.tmp/pytest` inside the
repository (git ignores it).
