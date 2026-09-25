# U1 · Data model and contracts · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Error formatter: every validation error names its field and the expected range | R-005 | done |
| 2 | Licence policy with canonical URIs and the two sets | R-102 | done |
| 3 | Ingestion contract: structure, rules across fields, flags; `POST /api/slide-cases/validate` | R-005, R-006 | done |
| 4 | Database: declarative base with a naming convention, `slide` and `asset`, engines with the pragmas, migration 0001, `app.db.migrate` | R-105, R-106 | done |
| 5 | Short ids in Crockford base 32, forgiving resolution | R-103 | done |
| 6 | Catalog contract and its builder: geoprivacy, media addresses, quality checks; `GET /api/slides/{id}`, `GET /api/slides` | R-104 | done |
| 7 | Schema exporter with `--check`; frontend workspace; TypeScript generation and drift check; CI web job | R-007, R-101 | done |
| 8 | Wiki: data contracts (with the data-model diagram, checked in both themes), the database; version 0.01.000 | (documentation and versioning standards) | done |

## Convergence verdict (2026-09-25, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-005 rejecting rules name field and range | `tests/contracts/test_ingest_contract.py::test_every_rejecting_rule_names_field_and_range` (48 cases) | pass |
| R-006 flags accepted and reported | `tests/contracts/test_ingest_contract.py::test_flagging_rules_accept_and_report` | pass |
| R-007 TypeScript types equal the schemas | `frontend/scripts/check-contract-drift.mjs` | pass |
| R-101 committed schemas equal the models | `tests/contracts/test_schema_export.py::test_committed_schemas_match_the_models` | pass |
| R-102 licence policy and normalisation | `tests/contracts/test_licence_policy.py::test_policy_sets_and_normalisation` | pass |
| R-103 short ids unique, case-insensitive | `tests/db/test_short_id.py::test_short_ids_are_unique_and_resolve_case_insensitively` | pass |
| R-104 obscured and private coordinates never leave | `tests/contracts/test_catalog_privacy.py::test_obscured_and_private_coordinates_never_leave` | pass |
| R-105 head migration matches the models | `tests/db/test_migrations.py::test_head_matches_models` | pass |
| R-106 pragmas on every connection | `tests/db/test_migrations.py::test_sqlite_pragmas_on_every_connection` | pass |

Also run: `pytest` 74 passed; `ruff check app tests scripts` clean; the five guards pass; `export_contracts.py
--check` OK; `tsc -b` clean; `vitest` 3 passed; `vite build` succeeds; the data-model diagram rendered headless
in both colour schemes and inspected.

Nothing unmet. Rules deferred by design to the unit that owns the registry or the file: anchor resolution and
placement acceptance (U7); readable headers, dimension limits and consistent plane sizes (U2, U5).
