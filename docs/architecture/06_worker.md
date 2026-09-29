# 06 · The processing worker

![The processing worker: jobs and their journal in SQLite, the worker claiming and running jobs in a one-process pool, the API streaming the journal, processing writing content-addressed files](svg/worker.svg)

Pyramiding a gigapixel slide takes half a minute of CPU and fusing a focal stack several minutes; neither can
happen inside a web request. The worker is a separate process that takes jobs from a queue in the catalog's
own database, runs them one at a time, and writes every step to a journal the browser follows live.

## 1. Jobs and their journal

A job has a kind, a JSON payload, a timeout, a status (`queued`, `running`, `succeeded`, `failed`), a count of
attempts, and a random public id (the API never exposes row numbers). Every step is an event in `job_event`,
numbered per job:

| Event | Written by | When |
|---|---|---|
| `queued` | whoever enqueues | the job is created |
| `started` | the worker | the job is claimed, with the attempt number |
| `log` | the job's process | its process id and kind |
| `progress` | the job's process | each step (a pyramid written, a tile of a fusion) |
| `requeued` | the worker | after a crash, or when the worker is asked to stop |
| `succeeded`, `failed` | the worker | the result, or the error |

Numbers come from one statement, `INSERT INTO job_event ... SELECT MAX(seq) + 1`, which SQLite runs atomically,
with `(job_id, seq)` unique, so the worker and the job's process never take the same number.

## 2. The worker

`python -m app.worker` loops:

1. **At start**, a job still marked `running` was interrupted by a crash or a restart. Its inputs are on disk and
   its steps are idempotent, so it is queued again (`requeued`) and counted as an attempt; after three
   interruptions it fails with the reason instead.
2. **It claims** the oldest queued job inside `BEGIN IMMEDIATE`, which takes SQLite's write lock before reading,
   so two claimers can never take the same job (tested with four threads on 24 jobs).
3. **It runs** the job in a `pebble` process pool with one process (spawn context, recycled after 25 jobs): one
   job at a time, in a process whose memory returns to the system when it ends. When the job's timeout passes,
   pebble kills the process; the standard library's pool cannot stop a running task.
4. **It records** the outcome: the result, the exception, "timed out after N s; the process was killed", or "the
   job's process died".

Asked to stop (SIGTERM or SIGINT), it cancels a running job, whose process is killed, and puts it back in the
queue without counting the attempt.

**A crash, as the gate measures it** (R-030): the worker and the job's process are killed together at step 2 of 8;
the job stays `running`; the restarted worker queues it again, runs it as attempt 2, and it succeeds with exactly
the output an uninterrupted run writes.

## 3. The event stream

`GET /api/jobs/{id}/events` is a Server-Sent Events stream: each message carries `id: <seq>`,
`event: <name>` and the event as JSON. It replays the journal after the event the client last saw (the
`Last-Event-ID` header a browser's `EventSource` sends when it reconnects, or `?after=`), follows new events
every half second, and ends after the terminal event. `retry: 2000` asks the browser to reconnect after two
seconds, and a comment every 15 seconds keeps idle connections open through proxies. A reconnect therefore
loses nothing and repeats nothing (R-032): after `Last-Event-ID: 4`, events 5 to the end arrive once, in order.

## 4. The processing jobs

**`process_asset`** reads an asset's source through the imaging engine (the reader's limits apply before any
decoding), writes its pyramid with the measured-fidelity ladder (or a clean JPEG for a macro photograph, without
EXIF), and marks the asset ready with its dimensions, bytes, SHA-256, PSNR and codec. When it makes the last plane
of a focal stack ready, it queues that stack's fusion, once.

**`fuse_stack`** reads the stored plane pyramids through the engine's tiled fusion and writes three assets: the
complex-wavelet composite (the default image), the variance composite, and the variance height map as a 16-bit
PNG (the depth readout's data, with the planes' depths in its caption). The job's process fuses the windows in
`fuse_workers` processes of its own, which the job's timeout and a stop take down with it (page 04, section 5). The stored height map equals the
engine's fusion of the stored planes, and on a synthetic stack it is within one plane of the known focus on at
least 90 percent of pixels.

**Storage keys are content addresses.** A file is stored as `{short id}/{asset id}-{digest}.{ext}`, where

$$\text{digest} = \operatorname{SHA\text{-}256}\big(v \,\|\, s \,\|\, p \,\|\, c\big)_{[0:12]}$$

with $v$ the pipeline version, $s$ the source's SHA-256 (or, for a fusion, the planes' keys), $p$ the plane and
$c$ the codec. Running a job again writes the same key and the same bytes; a replaced source or a new pipeline
writes a new key and removes the old file. That is what lets nginx cache tiles for 30 days (U3): a key never
names two different contents.

**`probe`** sleeps in steps and writes a small file: the worker's health check in production and the job the
queue gates use.

## 5. Operating it

```bash
python -m app.worker                                  # the worker (a service in production)
python -m app.jobs enqueue probe '{"steps": 3, "seconds": 2}'
python -m app.jobs wait <id> --seconds 120            # exit 0 when it succeeded
python -m app.jobs status <id>                        # the job and its whole journal
python -m app.jobs list
```

## 6. How it is verified

| Gate | Checks |
|---|---|
| `tests/worker/test_queue.py` | a real crash of the worker and its job, re-queued and completed with the same output; a timeout that kills the process; one job at a time, in one reused process; exclusive claims; the attempt limit; an unknown kind |
| `tests/worker/test_sse.py` | full replay, resumption after `Last-Event-ID` and `?after=`, nothing after the end, a live job followed to its end |
| `tests/worker/test_processing.py` | idempotent processing and new keys for new sources; a case processed end to end and served by the catalog, without GPS; stack fusion equal to the engine, queued once, idempotent, and kept out of the manifest's painted images |

## References

- pebble 5.2.2, process pools with timeouts. [github.com/noxdafox/pebble](https://github.com/noxdafox/pebble).
- SQLite, `BEGIN IMMEDIATE` and write-ahead logging. [sqlite.org/lang_transaction.html](https://www.sqlite.org/lang_transaction.html),
  [sqlite.org/wal.html](https://www.sqlite.org/wal.html).
- Server-Sent Events, WHATWG HTML Living Standard, section 9.2.
  [html.spec.whatwg.org/multipage/server-sent-events.html](https://html.spec.whatwg.org/multipage/server-sent-events.html).
