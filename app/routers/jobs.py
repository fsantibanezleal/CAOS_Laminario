"""Processing jobs: their status, and their events as a Server-Sent Events stream.

The stream replays the journal after the event the client last saw (the ``Last-Event-ID`` header a browser's
``EventSource`` sends when it reconnects, or ``?after=``), then follows new events as the worker writes them,
and ends after the job's terminal event. Each message carries ``id: <seq>``, ``event: <name>`` and the event
as JSON; a comment line every 15 seconds keeps idle connections open through proxies; ``retry: 2000`` asks the
browser to reconnect after two seconds.

Jobs are addressed by a random public id, never by their row number.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from app.contracts import catalog as c
from app.jobs import journal

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

POLL_SECONDS = 0.5
PING_SECONDS = 15.0


async def _job_row(request: Request, public_id: str):
    async with request.app.state.engine.connect() as conn:
        row = (await conn.execute(text(
            "SELECT id, public_id, kind, status, attempts, error, result_json, created_at, started_at, finished_at "
            "FROM job WHERE public_id = :pid"), {"pid": public_id})).first()
    if row is None:
        raise HTTPException(status_code=404, detail="no job with this id")
    return row


@router.get("/{public_id}", response_model=c.JobRecord)
async def read_job(public_id: str, request: Request) -> c.JobRecord:
    row = await _job_row(request, public_id)
    return c.JobRecord(
        id=row.public_id, kind=row.kind, status=row.status, attempts=row.attempts, error=row.error,
        result=json.loads(row.result_json) if row.result_json else None, created_at=row.created_at,
        started_at=row.started_at, finished_at=row.finished_at, events_url=f"/api/jobs/{row.public_id}/events",
    )


def message(event: journal.Event) -> str:
    record = c.JobEventRecord(seq=event.seq, event=event.event, data=event.data, at=event.created_at)
    return f"id: {event.seq}\nevent: {event.event}\ndata: {record.model_dump_json()}\n\n"


async def stream(request: Request, job_id: int, last_seq: int) -> AsyncIterator[str]:
    yield "retry: 2000\n\n"
    engine = request.app.state.engine
    last_ping = time.monotonic()
    while True:
        async with engine.connect() as conn:
            events = await conn.run_sync(journal.after, job_id, last_seq)
            status = (await conn.execute(text("SELECT status FROM job WHERE id = :id"), {"id": job_id})).scalar()
        for event in events:
            yield message(event)
            last_seq = event.seq
            if event.event in journal.TERMINAL:
                return
        if not events and status in journal.TERMINAL:
            return  # the terminal event was already delivered before this connection
        if time.monotonic() - last_ping >= PING_SECONDS:
            yield ": ping\n\n"
            last_ping = time.monotonic()
        if await request.is_disconnected():
            return
        await asyncio.sleep(POLL_SECONDS)


@router.get("/{public_id}/events")
async def job_events(public_id: str, request: Request,
                     last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
                     after: Annotated[int | None, Query(ge=0)] = None) -> StreamingResponse:
    row = await _job_row(request, public_id)
    last = after if after is not None else 0
    if last_event_id and last_event_id.isdigit():
        last = int(last_event_id)
    return StreamingResponse(stream(request, row.id, last), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
