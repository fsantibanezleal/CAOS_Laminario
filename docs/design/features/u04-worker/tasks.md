# U4 · The processing worker · tasks

| # | Task | Satisfies | Status |
|---|---|---|---|
| 1 | `job` and `job_event` tables; the asset's source path, PSNR and codec (migration 0003) | R-030 to R-033 | done |
| 2 | The queue: enqueue, atomic claim, finish, put back, re-queue after a crash, the attempt limit | R-030, R-405, R-406 | done |
| 3 | The journal: one-statement numbering, reading after a number, text timestamps | R-032 | done |
| 4 | The worker: one-process pebble pool, killing timeouts, stop handling, unknown kinds | R-031, R-033 | done |
| 5 | Job status and the Server-Sent Events stream; job records in the catalog contract and TypeScript | R-032 | done |
| 6 | `process_asset` with content-addressed keys; `fuse_stack` with both composites and the height map; fusion queued by the last plane; `probe` | R-401 to R-404 | done |
| 7 | Operator commands `python -m app.jobs` | (the deploy gate of U16) | done |
| 8 | Manifests without the height map | R-403 | done |
| 9 | Wiki page 06 with its diagram (checked in both themes); design; guide section; version 0.04.000 | (documentation and versioning standards) | done |

## Convergence verdict (2026-09-29, before the pull request)

| Requirement | Gate | Result |
|---|---|---|
| R-030 restart re-queues and completes | `tests/worker/test_queue.py::test_restart_requeues_and_completes` (worker and job process killed at step 2 of 8, restarted, attempt 2 succeeds with the uninterrupted output) | pass (Windows and Ubuntu) |
| R-031 timeout kills | `tests/worker/test_queue.py::test_timeout_kills` (the job's process is gone) | pass (both) |
| R-032 replay after reconnect | `tests/worker/test_sse.py::test_replay_after_reconnect` | pass (both) |
| R-033 one heavy job at a time | `tests/worker/test_queue.py::test_single_heavy_job` (no overlap, one reused process) | pass (both) |
| R-401 idempotent processing | `tests/worker/test_processing.py::test_process_asset_is_idempotent` | pass (both) |
| R-402 a case end to end | `tests/worker/test_processing.py::test_worker_processes_a_case_end_to_end` | pass (both) |
| R-403 fusion equals the engine | `tests/worker/test_processing.py::test_fuse_stack_stores_composites` | pass (both) |
| R-404 fusion queued once | `tests/worker/test_processing.py::test_fuse_stack_stores_composites` | pass (both) |
| R-405 exclusive claims | `tests/worker/test_queue.py::test_claims_are_exclusive` | pass (both) |
| R-406 the attempt limit | `tests/worker/test_queue.py::test_interrupted_too_often_fails` | pass (both) |

The full suite ran on the production host (Ubuntu 24.04, libvips 8.15.1, Docker) with the fixtures and with
deprecation warnings as errors, and on the development machine (Windows, libvips 8.18.6), where only the three
container gates of U3 are skipped; the counts are in the pull request.

Unmet: none. Owed by later units: the upload hook that sets `source_path` and queues processing (U5), the base
import that queues from the vault (U8), progress in the contribution page (U12), the worker as a service with the
probe as its production gate (U16).
