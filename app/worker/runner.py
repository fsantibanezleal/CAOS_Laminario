"""The worker loop.

1. On start, jobs left ``running`` by a crash or a restart are queued again (or failed after too many tries).
2. The oldest queued job is claimed and run in a ``pebble`` process pool with one process: jobs run one at a
   time (the design runs at most one heavy job), in a separate process whose memory is returned when it ends,
   and a job that outlives its timeout is killed with its process, not merely abandoned.
3. The outcome (result, error or timeout) is recorded with its terminal event.
4. A stop request (SIGTERM, SIGINT or ``stop()``) ends the loop; a job still running is cancelled, its process
   killed, and it goes back to the queue without counting as an attempt.

The pool recycles its process after ``MAX_TASKS_PER_PROCESS`` jobs, so a slow leak in a native library cannot
grow for ever.
"""

from __future__ import annotations

import concurrent.futures
import logging
import multiprocessing
import os
import signal
import socket
import threading
import time
import traceback

from pebble import ProcessExpired, ProcessPool

from app.config import Settings
from app.db.engine import database_path, make_sync_engine
from app.db.migrate import upgrade_to_head
from app.jobs import kinds, queue
from app.services import cases

log = logging.getLogger("laminario.worker")

POLL_SECONDS = 1.0
MAX_TASKS_PER_PROCESS = 25


class Worker:
    def __init__(self, settings: Settings | None = None, name: str | None = None):
        self.settings = settings or Settings()
        self.name = name or f"{socket.gethostname()}:{os.getpid()}"
        self.database = database_path(self.settings)
        self._stop = threading.Event()

    def stop(self, *_args) -> None:
        self._stop.set()

    def install_signal_handlers(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self.stop)

    def run(self, max_jobs: int | None = None, deadline: float | None = None) -> int:
        """Process jobs until stopped, after ``max_jobs``, or past ``deadline`` (``time.monotonic``); returns how many
        were run. The service runs without either; tests pass both so a missing job cannot hang them."""
        upgrade_to_head(self.database)
        engine = make_sync_engine(self.database)
        done = 0
        try:
            for job_id in queue.requeue_interrupted(engine):
                log.info("job %s was interrupted and is queued again", job_id)
            context = multiprocessing.get_context("spawn")
            pool = ProcessPool(max_workers=1, max_tasks=MAX_TASKS_PER_PROCESS, context=context)
            try:
                while (not self._stop.is_set() and (max_jobs is None or done < max_jobs)
                       and (deadline is None or time.monotonic() < deadline)):
                    job = queue.claim(engine, self.name)
                    if job is None:
                        self._stop.wait(POLL_SECONDS)
                        continue
                    self._run_one(engine, pool, job)
                    done += 1
                    if not pool.active:
                        # A job's process left the pool unusable (an answer it could not send back): a new pool
                        # takes the next job, where the old one refused every job after it and stopped the worker.
                        log.warning("the process pool failed after job %s; starting a new one", job.id)
                        pool.stop()
                        pool.join()
                        pool = ProcessPool(max_workers=1, max_tasks=MAX_TASKS_PER_PROCESS, context=context)
            finally:
                pool.close()
                pool.join()
        finally:
            engine.dispose()
        return done

    def _run_one(self, engine, pool: ProcessPool, job: queue.ClaimedJob) -> None:
        log.info("job %s (%s) attempt %s", job.id, job.kind, job.attempt)
        if job.kind not in kinds.KINDS:
            queue.finish(engine, job.id, "failed", error=f"unknown job kind {job.kind!r}")
            return
        try:
            future = pool.schedule(kinds.execute, args=(job.id, job.public_id, job.kind, job.payload, self.settings),
                                   timeout=job.timeout_s)
        except RuntimeError as exc:  # the pool had failed: the job waits for the next one
            queue.put_back(engine, job.id, f"the process pool had failed: {exc}", count_attempt=False)
            return
        while True:
            finished, _ = concurrent.futures.wait([future], timeout=POLL_SECONDS)
            if finished:
                break
            if self._stop.is_set():
                future.cancel()  # pebble terminates the running process
                queue.put_back(engine, job.id, "the worker was asked to stop", count_attempt=False)
                return
        failure: str | None = None
        try:
            result = future.result()
        except concurrent.futures.TimeoutError:
            failure = f"timed out after {job.timeout_s} s; the process was killed"
        except ProcessExpired as exc:
            failure = f"the job's process died ({exc.exitcode})"
        except concurrent.futures.CancelledError:
            queue.put_back(engine, job.id, "cancelled while stopping", count_attempt=False)
            return
        except Exception as exc:  # the job raised: record what and where
            failure = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        if failure is None:
            queue.finish(engine, job.id, "succeeded", result=result)
        else:
            queue.finish(engine, job.id, "failed", error=failure)
        try:
            # A contribution may have been waiting for this job: publish it, or send it back with the reason.
            cases.after_job(engine, job.kind, job.payload, failure is not None, failure)
        except Exception:  # the job's outcome is recorded; a failed check is logged, never fatal to the worker
            log.exception("checking the case of job %s failed", job.id)
