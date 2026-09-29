# U5 · Resumable uploads · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | Research: tusd v2.10.1, its hooks and their failure semantics (dossier 08) | (research) | done |
| 2 | The `upload` table (migration 0005) and the upload settings (quotas, limits, the disk rule, folders) | R-042, R-043 | done |
| 3 | Content sniffing from bytes, ZIP containers by their contents | R-041, R-503 | done |
| 4 | The pre-create policy and the hook endpoint; post-finish queues verification; post-terminate | R-042, R-043, R-502 | done |
| 5 | The verification job: size, SHA-256, sniffing, safe unpacking, readable header, source store, processing queued, refusals deleted and explained | R-040, R-041 | done |
| 6 | Upload records for the contributor; the upload record in the contract and TypeScript | (contracts) | done |
| 7 | tusd compose file (pinned, loopback, read-only) and nginx's `/files/` | R-501 | done |
| 8 | Tests with the real tusd and the real worker; the worker's deadline for bounded runs | R-040 to R-043, R-501 to R-503 | done |
| 9 | Wiki page 08 with its diagram (both themes checked), the tusd card, design, guide section; version 0.06.000 | (documentation and versioning standards) | done |

## Convergence verdict (2026-09-29, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-040 resumed upload keeps the SHA-256 | `tests/uploads/test_tus.py::test_resume_after_interruption` (connection dropped mid-body, offset read, rest sent; then verified and processed to a ready image) | pass (Windows and Ubuntu) |
| R-041 wrong types deleted and named | `tests/uploads/test_tus.py::test_disallowed_type_rejected` | pass (both) |
| R-042 quotas refuse creation | `tests/uploads/test_tus.py::test_quota_refused` | pass (both) |
| R-043 the disk rule | `tests/uploads/test_tus.py::test_tier_a_budget_blocks_wsi` | pass (both) |
| R-501 the tusd compose file | `tests/uploads/test_tus.py::test_tusd_compose_file_on_loopback` | pass on the production host |
| R-502 authorisation | `tests/uploads/test_tus.py::test_uploads_are_authorised` | pass (both) |
| R-503 archives | `tests/uploads/test_tus.py::test_archives_are_recognised` | pass (both) |

The first run on the production host hung: tusd delivers post-finish after it has answered the client, the test
stopped tusd before the hook arrived, and the worker then waited for a job that never came. The tests now wait for
the upload to be recorded as received, and the worker takes a deadline in tests. The full suites ran on the
production host (with fixtures, the tusd binary and Docker, deprecation warnings as errors) and on the development
machine; the counts are in the pull request.

Unmet: none. Owed by later units: Uppy over tus in the contribution page (U12); the service account, folders and
the compose file installed on the host (U16).
