"""The durable job queue, in the same SQLite database as the catalog.

- ``enqueue`` adds a job in the ``queued`` state with its first event.
- ``claim`` takes the oldest queued job inside ``BEGIN IMMEDIATE``, so no two workers could take the same one,
  and marks it ``running`` with one more attempt.
- ``finish`` records the outcome, the result or the error, and the terminal event.
- ``requeue_interrupted`` runs when the worker starts: a job left ``running`` was interrupted by a crash or a
  restart. Its inputs are on disk and its steps are idempotent, so it goes back to ``queued`` (event
  ``requeued``) until it has been interrupted ``max_attempts`` times, then it fails with the reason.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db.base import utcstamp
from app.jobs import journal

DEFAULT_TIMEOUT_S = {"probe": 600, "process_asset": 3600, "fuse_stack": 7200}
MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class ClaimedJob:
    id: int
    public_id: str
    kind: str
    payload: dict
    timeout_s: int
    attempt: int


def enqueue(engine: Engine, kind: str, payload: dict, *, timeout_s: int | None = None, heavy: bool = True,
            slide_id: int | None = None, max_attempts: int = MAX_ATTEMPTS) -> tuple[int, str]:
    """Add a job; returns (id, public id)."""
    public_id = secrets.token_hex(12)
    with engine.begin() as conn:
        job_id = conn.execute(
            text("INSERT INTO job (public_id, kind, status, heavy, payload_json, timeout_s, attempts, max_attempts, "
                 "slide_id, created_at) VALUES (:pid, :kind, 'queued', :heavy, :payload, :timeout, 0, :max, "
                 ":slide, :now) RETURNING id"),
            {"pid": public_id, "kind": kind, "heavy": heavy, "payload": json.dumps(payload),
             "timeout": timeout_s or DEFAULT_TIMEOUT_S.get(kind, 3600), "max": max_attempts, "slide": slide_id,
             "now": utcstamp()},
        ).scalar_one()
    journal.record(engine, job_id, "queued", {"kind": kind})
    return job_id, public_id


def claim(engine: Engine, worker: str) -> ClaimedJob | None:
    """The oldest queued job, now running; None when the queue is empty."""
    with engine.connect() as conn:
        conn.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            row = conn.execute(text("SELECT id, public_id, kind, payload_json, timeout_s, attempts FROM job "
                                    "WHERE status = 'queued' ORDER BY id LIMIT 1")).first()
            if row is None:
                conn.exec_driver_sql("COMMIT")
                return None
            conn.execute(text("UPDATE job SET status = 'running', attempts = attempts + 1, worker = :worker, "
                              "started_at = :now, finished_at = NULL WHERE id = :id"),
                         {"worker": worker, "now": utcstamp(), "id": row.id})
            conn.exec_driver_sql("COMMIT")
        except Exception:
            conn.exec_driver_sql("ROLLBACK")
            raise
    job = ClaimedJob(row.id, row.public_id, row.kind, json.loads(row.payload_json), row.timeout_s, row.attempts + 1)
    journal.record(engine, job.id, "started", {"attempt": job.attempt, "worker": worker})
    return job


def finish(engine: Engine, job_id: int, status: str, *, result: dict | None = None, error: str | None = None) -> None:
    """Record a job's outcome and its terminal event."""
    if status not in journal.TERMINAL:
        raise ValueError(f"not a terminal status: {status}")
    with engine.begin() as conn:
        conn.execute(text("UPDATE job SET status = :status, result_json = :result, error = :error, "
                          "finished_at = :now WHERE id = :id"),
                     {"status": status, "result": json.dumps(result) if result is not None else None,
                      "error": (error or "")[:500] or None, "now": utcstamp(), "id": job_id})
    data = {"result": result} if result is not None else {}
    if error:
        data["error"] = error[:500]
    journal.record(engine, job_id, status, data)


def put_back(engine: Engine, job_id: int, reason: str, *, count_attempt: bool) -> None:
    """Return a running job to the queue (a deliberate stop does not count as an attempt)."""
    with engine.begin() as conn:
        conn.execute(text("UPDATE job SET status = 'queued', worker = NULL, started_at = NULL, "
                          "attempts = attempts - :undo WHERE id = :id"),
                     {"undo": 0 if count_attempt else 1, "id": job_id})
    journal.record(engine, job_id, "requeued", {"reason": reason})


def requeue_interrupted(engine: Engine) -> list[int]:
    """At worker start: jobs left running were interrupted; queue them again or fail them after too many tries."""
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, attempts, max_attempts FROM job WHERE status = 'running'")).all()
    requeued = []
    for row in rows:
        if row.attempts >= row.max_attempts:
            finish(engine, row.id, "failed", error=f"interrupted {row.attempts} times; not retried again")
        else:
            put_back(engine, row.id, "the worker stopped while the job ran", count_attempt=True)
            requeued.append(row.id)
    return requeued
