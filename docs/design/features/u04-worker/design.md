# U4 · The processing worker · design

How the worker runs, with its diagram and the job kinds, is in the wiki page
[06 The processing worker](../../../architecture/06_worker.md); this page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| `job` and `job_event` tables; asset columns `source_path`, `psnr_db`, `codec` | migration 0003, `app/db/models.py` |
| The queue: enqueue, claim, finish, put back, re-queue after a crash | `app/jobs/queue.py` |
| The journal: numbered events, read after a number | `app/jobs/journal.py` |
| The job kinds: `probe`, `process_asset`, `fuse_stack` | `app/jobs/kinds.py` |
| The worker process | `app/worker/runner.py`, `python -m app.worker` |
| Job status and the event stream | `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events` (`app/routers/jobs.py`) |
| Operator commands | `python -m app.jobs enqueue / status / list / wait` |
| The job records of the catalog contract | `JobRecord`, `JobEventRecord` (and their TypeScript types) |

## Decisions

- **The ADR-0048 pattern, made durable (ADR-0077).** Jobs live in the catalog's SQLite database, in write-ahead-log
  mode; no broker. A separate process claims them; the API never runs one.
- **One process in the pool.** `pebble.ProcessPool(max_workers=1)` with the spawn context: jobs run one at a time
  (R-033), each in a process whose memory returns to the system when it ends, recycled after 25 jobs. pebble,
  unlike the standard library's pool, kills a running task when its timeout passes (R-031).
- **Claims are atomic.** `BEGIN IMMEDIATE` takes the write lock before the oldest queued job is read, so two
  claimers cannot take the same job (R-405), and a busy timeout of 5 s makes them wait instead of failing.
- **Journal numbers come from one statement.** `INSERT ... SELECT MAX(seq) + 1` is one atomic statement in
  SQLite and `(job_id, seq)` is unique; the child process and the worker both write events without taking the
  same number.
- **A crash re-queues; a stop puts back.** At start, a job left `running` was interrupted: it is queued again
  and counted as an attempt, and after `max_attempts` (3) it fails with the reason (R-406). A deliberate stop
  cancels the running job (pebble kills its process) and puts it back without counting.
- **Jobs are idempotent because outputs are content-addressed.** A storage key is
  `{short id}/{asset id}-{digest}`, the digest taken from the source's SHA-256 (or the stored planes' keys) and a
  pipeline version. Running a job again writes the same key and the same bytes (R-030, R-401); a new source or
  a new pipeline writes a new key and removes the old file, so a tile cached under a key never goes stale (U3).
- **Fusion follows the planes.** The job that makes the last plane of a stack ready queues the stack's fusion,
  once (R-404). Fusion reads the stored plane pyramids through the U2 engine's tiled fusion, writes both
  composites as pyramids and the variance height map as a 16-bit PNG, the depth readout's data (F-015).
- **Timestamps as text in raw SQL.** Python 3.12 deprecates sqlite3's datetime adapter; the queue and the
  journal write ISO text, which the models read back as datetimes.
- **Jobs are public by a random id.** The API addresses jobs by a 24-character random id, not by row number.

## Interfaces used by later units

- U5 (uploads): each finished upload sets its asset's `source_path` and queues `process_asset`; the contributor's
  page follows the job's event stream.
- U8 (base collection): the import queues the same jobs from the vault.
- U12 (contribute): progress bars read the event stream; a reconnect resumes where it stopped.
- U16 (deploy): the worker runs as its own service next to the API; `python -m app.jobs enqueue probe` and
  `wait` are the production gate that the worker is alive.
