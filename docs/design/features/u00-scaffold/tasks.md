# U0 · Scaffold · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Copy the template guards and community files; extend the residue guard to forbid a Pages workflow | R-004 | done |
| 2 | Write `check_repo_hygiene.py` and its tests with negative controls | R-002 | done |
| 3 | Keep the content-standards, CI-budget and design-document guards | R-001, R-003 | done |
| 4 | CI workflow: lint and guards on `develop` and `main`, concurrency, timeouts | R-003 | done |
| 5 | Server skeleton: settings, version, `GET /api/health`, test | R-008 | done |
| 6 | Local scripts `00`, `01`, `03` in PowerShell and bash, executable mode | (local-run standard) | done |
| 7 | Wiki: index, architecture overview and diagram (checked in light and dark), run-locally guide, this design | (documentation standard) | done |
| 8 | README, CHANGELOG, `VERSION` 0.00.000 | (versioning standard) | done |

## Convergence verdict (2026-09-24, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-001 content standards | `scripts/check_content_standards.py` | pass |
| R-002 repository hygiene | `scripts/check_repo_hygiene.py` (and `tests/test_repo_guards.py`, 7 cases including negative controls) | pass |
| R-003 CI budget | `scripts/check_ci_budget.py` | pass |
| R-004 no Pages workflow | `scripts/check_template_residue.py` | pass |
| R-008 health endpoint | `tests/test_health.py::test_health_reports_product_and_version` | pass |

Also run: `pytest` 9 passed; `ruff check app tests scripts` clean; `check_sdd.py` passes on the design document
and this feature's requirements; every relative link in the tracked Markdown resolves; the three `.sh` scripts are
mode 100755; the architecture diagram was rendered headless in both colour schemes and inspected.

Nothing unmet.
