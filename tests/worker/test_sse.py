"""The job event stream: complete replay, resumption after the last event seen, live following."""

from __future__ import annotations

import json
import threading
import time

from fastapi.testclient import TestClient

from app.jobs import journal, queue
from app.main import create_app

from .support import sandbox


def parse(lines) -> list[dict]:
    """Server-Sent Events into dicts with ``id``, ``event`` and the decoded ``data``."""
    messages, current = [], {}
    for line in lines:
        if line == "":
            if "data" in current:
                messages.append(current)
            current = {}
        elif line.startswith(":") or line.startswith("retry:"):
            continue
        else:
            field, _, value = line.partition(": ")
            current[field] = json.loads(value) if field == "data" else value
    return messages


def finished_job(engine, steps: int = 6) -> str:
    job_id, public_id = queue.enqueue(engine, "probe", {"steps": steps})
    queue.claim(engine, "test")
    for step in range(steps):
        journal.record(engine, job_id, "progress", {"step": step + 1})
    queue.finish(engine, job_id, "succeeded", result={"ok": True})
    return public_id


# R-032
def test_replay_after_reconnect(tmp_path):
    settings, engine = sandbox(tmp_path)
    public_id = finished_job(engine)  # queued, started, 6 progress, succeeded: 9 events
    with TestClient(create_app(settings)) as client:
        with client.stream("GET", f"/api/jobs/{public_id}/events") as response:
            assert response.headers["content-type"].startswith("text/event-stream")
            everything = parse(response.iter_lines())
        assert [int(m["id"]) for m in everything] == list(range(1, 10))
        assert everything[0]["event"] == "queued" and everything[-1]["event"] == "succeeded"
        assert all(m["data"]["seq"] == int(m["id"]) and m["data"]["event"] == m["event"] for m in everything)

        # a browser reconnecting sends the last id it saw: it gets every later event, once, in order
        with client.stream("GET", f"/api/jobs/{public_id}/events", headers={"Last-Event-ID": "4"}) as response:
            resumed = parse(response.iter_lines())
        assert [int(m["id"]) for m in resumed] == list(range(5, 10))
        assert [m["data"] for m in resumed] == [m["data"] for m in everything[4:]]

        with client.stream("GET", f"/api/jobs/{public_id}/events?after=7") as response:
            assert [int(m["id"]) for m in parse(response.iter_lines())] == [8, 9]

        with client.stream("GET", f"/api/jobs/{public_id}/events", headers={"Last-Event-ID": "9"}) as response:
            assert parse(response.iter_lines()) == [], "after the terminal event the stream just ends"

        record = client.get(f"/api/jobs/{public_id}").json()
        assert record["status"] == "succeeded" and record["result"] == {"ok": True}
        assert record["events_url"] == f"/api/jobs/{public_id}/events"
        assert client.get("/api/jobs/not-a-job").status_code == 404


def test_stream_follows_a_running_job(tmp_path):
    settings, engine = sandbox(tmp_path)
    job_id, public_id = queue.enqueue(engine, "probe", {})
    queue.claim(engine, "test")

    def work():
        for step in range(5):
            time.sleep(0.3)
            journal.record(engine, job_id, "progress", {"step": step + 1})
        queue.finish(engine, job_id, "succeeded", result={"done": 5})

    writer = threading.Thread(target=work)
    with TestClient(create_app(settings)) as client:
        started = time.monotonic()
        writer.start()
        with client.stream("GET", f"/api/jobs/{public_id}/events") as response:
            live = parse(response.iter_lines())
        writer.join(10)
    assert [m["event"] for m in live] == ["queued", "started"] + ["progress"] * 5 + ["succeeded"]
    assert [int(m["id"]) for m in live] == list(range(1, 9))
    assert time.monotonic() - started >= 1.5, "the stream waited for events written after it opened"
