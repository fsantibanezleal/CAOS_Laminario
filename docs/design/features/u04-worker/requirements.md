# U4 · The processing worker · requirements

R-030 to R-033 moved here verbatim from the design document. R-401 to R-406 are this unit's own.

```
R-030  WHEN the worker restarts while a job is running, THE worker SHALL re-queue the job and complete it with the same outputs.
       Gate: tests/worker/test_queue.py::test_restart_requeues_and_completes

R-031  IF a job exceeds its timeout, THEN THE worker SHALL kill its process and mark the job failed with the reason.
       Gate: tests/worker/test_queue.py::test_timeout_kills

R-032  WHEN a client reconnects to a job's event stream with a last event id, THE API SHALL replay every later event in order.
       Gate: tests/worker/test_sse.py::test_replay_after_reconnect

R-033  THE worker SHALL run at most one heavy job at a time.
       Gate: tests/worker/test_queue.py::test_single_heavy_job

R-401  WHEN an asset is processed again from the same source, THE worker SHALL write the same storage key and the same bytes, and WHEN the source changes, a new key, removing the file of the old one.
       Gate: tests/worker/test_processing.py::test_process_asset_is_idempotent

R-402  WHEN a slide case's assets are processed, THE catalog SHALL serve each one as ready, the micro images through IIIF and the macro photographs as clean images without GPS.
       Gate: tests/worker/test_processing.py::test_worker_processes_a_case_end_to_end

R-403  WHEN a focal stack is fused, THE stored height map SHALL equal the imaging engine's fusion of the stored planes, and both composites SHALL be stored as ready assets.
       Gate: tests/worker/test_processing.py::test_fuse_stack_stores_composites

R-404  WHEN the last plane of a stack becomes ready, THE worker SHALL queue the stack's fusion exactly once.
       Gate: tests/worker/test_processing.py::test_fuse_stack_stores_composites

R-405  WHEN several claimers take jobs at the same time, THE queue SHALL give every job to exactly one of them.
       Gate: tests/worker/test_queue.py::test_claims_are_exclusive

R-406  IF a job is interrupted as many times as its attempt limit, THEN THE worker SHALL fail it with the reason instead of queueing it again.
       Gate: tests/worker/test_queue.py::test_interrupted_too_often_fails
```
