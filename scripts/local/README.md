# Local scripts

Run them in order from the repository root. Each one ends by printing the next command, and refuses with
the command to fix it when a prerequisite is missing. PowerShell first; the bash scripts do the same.

| Script | Does |
|---|---|
| `00_install-prereqs` | Checks Python 3.12, Node 22 to 24, git and Docker. `-Install` (PowerShell) installs what is missing with winget; the default only checks. |
| `01_init` | Creates `.venv` with Python 3.12, installs `requirements-dev.txt`, and writes `.env` from `LAMINARIO_ENV_SOURCE` when set, else from `.env.example`. Idempotent; `-Force` (bash: `--force`) rebuilds the venv. |
| `03_dev` | Runs the API on `http://127.0.0.1:8147` with auto-reload; refuses a port already in use. |

`02_generate-data` arrives with the base collection (unit U8).

## Release gates, run locally before every push

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app tests scripts
.\.venv\Scripts\python.exe scripts\check_repo_hygiene.py
.\.venv\Scripts\python.exe scripts\check_template_residue.py
.\.venv\Scripts\python.exe scripts\check_content_standards.py
.\.venv\Scripts\python.exe scripts\check_ci_budget.py
.\.venv\Scripts\python.exe scripts\check_sdd.py
```

CI runs only the lint and the guards; the test suite is the local gate.
