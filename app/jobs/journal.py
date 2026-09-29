"""The event journal: every step of every job, numbered per job.

The worker and the process running a job both write here; the API reads it and streams it over SSE. Each
event gets the next number for its job inside one ``INSERT ... SELECT``, which SQLite runs as one atomic
statement, so two writers never take the same number (``(job_id, seq)`` is also unique). A client that
reconnects sends the last number it saw and receives every later event, in order, exactly once.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

TERMINAL = ("succeeded", "failed", "cancelled")


@dataclass(frozen=True)
class Event:
    seq: int
    event: str
    data: dict
    created_at: datetime


def record(engine: Engine, job_id: int, event: str, data: dict | None = None) -> int:
    """Append an event to a job's journal and return its number."""
    payload = json.dumps(data or {}, separators=(",", ":"), default=str)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO job_event (job_id, seq, event, data_json, created_at) "
                "SELECT :job, COALESCE(MAX(seq), 0) + 1, :event, :data, CURRENT_TIMESTAMP "
                "FROM job_event WHERE job_id = :job"
            ),
            {"job": job_id, "event": event, "data": payload},
        )
        return conn.execute(text("SELECT MAX(seq) FROM job_event WHERE job_id = :job"), {"job": job_id}).scalar_one()


def after(conn: Connection, job_id: int, seq: int, limit: int = 500) -> list[Event]:
    """Events of a job with a number greater than ``seq``, in order."""
    rows = conn.execute(
        text("SELECT seq, event, data_json, created_at FROM job_event WHERE job_id = :job AND seq > :seq "
             "ORDER BY seq LIMIT :limit"),
        {"job": job_id, "seq": seq, "limit": limit},
    ).all()
    return [Event(r.seq, r.event, json.loads(r.data_json),
                  r.created_at if isinstance(r.created_at, datetime) else datetime.fromisoformat(str(r.created_at)))
            for r in rows]
