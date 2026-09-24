# U0 · Scaffold · design

## What the unit delivers

The repository base every later unit builds on, instantiated from the product template with its example removed:

- `app/`: the server application, activated from the start because Laminario needs accounts, uploads and
  processing. In this unit it holds the settings (`app/config.py`, environment prefix `LAMINARIO_`), the version
  read once from `VERSION` (`app/version.py`), and the FastAPI application with one route, `GET /api/health`.
- Guards, each a standard-library script so continuous integration runs them before installing anything:
  `check_repo_hygiene.py` (new: nothing that belongs outside git may be tracked, including slide, pyramid and
  database files, files over 5 MB, and local machine paths), `check_template_residue.py` (extended to forbid a
  GitHub Pages deploy workflow), `check_content_standards.py`, `check_ci_budget.py`, `check_sdd.py`.
- Continuous integration (`.github/workflows/ci.yaml`): on push to `develop` and `main` and by hand only, with a
  concurrency group and a timeout per job; it runs the lint and the guards, never the test suite.
- The numbered local scripts `00_install-prereqs`, `01_init` and `03_dev` in PowerShell and bash.
- Identity and community files, the `VERSION` file (0.00.000) and the changelog.
- The wiki: index, architecture overview with its diagram, the run-locally guide, this feature design.

## Interfaces

| Interface | Contract |
|---|---|
| `GET /api/health` | `200 {"status": "ok", "product": "laminario", "version": "<VERSION>"}`. The product name lets a gate prove it reached Laminario and not another program on the same port. |
| Environment | `LAMINARIO_ENV`, `LAMINARIO_PUBLIC_BASE_URL`, `LAMINARIO_DATA_ROOT`, `LAMINARIO_TEST_TMP`, documented in `.env.example`; empty values fall back to the defaults. |

## Decisions

- The application source is imported from the repository root (`uvicorn app.main:app`); it is not an installable
  package, and `pyproject.toml` carries tool configuration only.
- Test temporary files go to `LAMINARIO_TEST_TMP` or `.tmp/pytest`, never to the system drive's temporary folder
  and never to the repository's data.
- The test client uses `httpx2`, which Starlette 1.7 asks for in place of `httpx`.
