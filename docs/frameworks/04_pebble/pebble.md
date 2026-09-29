# pebble

## What and why

pebble provides process pools whose tasks can be timed out and cancelled while they run: the task's process is
terminated and replaced. The standard library's `ProcessPoolExecutor` cannot stop a running task. ADR-0048 chose
it for CPU-bound jobs without a message broker; ADR-0077 made that pattern durable for Laminario's worker.

## Install (exact, verified)

`pebble==5.2.2` (in `requirements-api.txt`), pure Python, Windows and Linux.

## Usage

```python
import multiprocessing
from pebble import ProcessPool

with ProcessPool(max_workers=1, max_tasks=25, context=multiprocessing.get_context("spawn")) as pool:
    future = pool.schedule(work, args=(job_id,), timeout=3600)
    result = future.result()   # raises TimeoutError after 3600 s; the process has been killed
```

## Applying it here

`app/worker/runner.py` runs every job in a pool of one process: one job at a time (R-033), a fresh process every
25 jobs, a timeout that kills the job's process (R-031), and `future.cancel()` to stop a running job when the
worker is asked to stop.

## Caveats and licence

- With the spawn context the child imports the parent's main module; a script run from standard input cannot
  host the pool (a harness problem, never the worker's, which runs as `python -m app.worker`).
- A job's process that dies raises `ProcessExpired`, recorded as "the job's process died".
- LGPL-3.0; used unmodified as a dependency.
