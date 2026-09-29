"""The durable queue and the worker: restart, timeout, one job at a time, exclusive claims."""

from __future__ import annotations

import hashlib
import threading

from app.jobs import journal, queue
from app.worker.runner import Worker

from .support import events, job, kill_tree, pid_alive, sandbox, start_worker, stop, wait_until


def child_pid(engine, job_id: int) -> int | None:
    for event in events(engine, job_id):
        if event.event == "log" and "pid" in event.data:
            return event.data["pid"]
    return None


# R-030
def test_restart_requeues_and_completes(tmp_path, monkeypatch):
    settings, engine = sandbox(tmp_path, monkeypatch)
    job_id, public_id = queue.enqueue(engine, "probe", {"steps": 8, "seconds": 8})
    log = tmp_path / "worker.log"
    first = start_worker(settings, log)
    try:
        wait_until(lambda: any(e.event == "progress" and e.data.get("step", 0) >= 2 for e in events(engine, job_id)),
                   60, "the job's second step")
        crashed_child = child_pid(engine, job_id)
        kill_tree(first)  # a crash: the worker and the job's process die mid-run
    finally:
        stop(first)
    assert job(engine, job_id).status == "running", "the crash left the job marked running"
    assert crashed_child and not pid_alive(crashed_child), "the job's process died with the worker"
    output = settings.data_root / "probes" / f"{public_id}.txt"
    assert not output.exists(), "the interrupted run did not get as far as its output"

    second = start_worker(settings, log)
    try:
        wait_until(lambda: job(engine, job_id).status in journal.TERMINAL, 90, "the requeued job's end")
    finally:
        stop(second)
    row = job(engine, job_id)
    assert row.status == "succeeded", (row.error, log.read_text(errors="replace")[-2000:])
    assert row.attempts == 2
    names = [e.event for e in events(engine, job_id)]
    assert names.count("started") == 2 and "requeued" in names and names[-1] == "succeeded"
    expected = f"probe {public_id} steps=8 seconds=8\n"
    assert output.read_text(encoding="utf-8") == expected, "the same output as an uninterrupted run"
    assert f'"sha256": "{hashlib.sha256(expected.encode()).hexdigest()}"' in row.result_json


# R-031
def test_timeout_kills(tmp_path, monkeypatch):
    settings, engine = sandbox(tmp_path, monkeypatch)
    job_id, _ = queue.enqueue(engine, "probe", {"steps": 60, "seconds": 60}, timeout_s=3)
    assert Worker(settings).run(max_jobs=1) == 1
    row = job(engine, job_id)
    assert row.status == "failed"
    assert row.error == "timed out after 3 s; the process was killed"
    pid = child_pid(engine, job_id)
    assert pid is not None
    wait_until(lambda: not pid_alive(pid), 10, "the timed-out process's end")
    assert events(engine, job_id)[-1].event == "failed"


# R-033
def test_single_heavy_job(tmp_path, monkeypatch):
    settings, engine = sandbox(tmp_path, monkeypatch)
    ids = [queue.enqueue(engine, "probe", {"steps": 2, "seconds": 1})[0] for _ in range(3)]
    assert Worker(settings).run(max_jobs=3) == 3
    rows = sorted((job(engine, i) for i in ids), key=lambda r: r.started_at)
    assert all(r.status == "succeeded" for r in rows)
    for earlier, later in zip(rows, rows[1:], strict=False):
        assert earlier.finished_at <= later.started_at, "two jobs ran at the same time"
    pids = {child_pid(engine, i) for i in ids}
    assert len(pids) == 1, "one process, reused, ran them one after the other"


def test_claims_are_exclusive(tmp_path):
    _, engine = sandbox(tmp_path)
    ids = {queue.enqueue(engine, "probe", {})[0] for _ in range(24)}
    claimed: list[int] = []
    lock = threading.Lock()

    def claimer(name: str):
        while (claim := queue.claim(engine, name)) is not None:
            with lock:
                claimed.append(claim.id)

    threads = [threading.Thread(target=claimer, args=(f"w{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert sorted(claimed) == sorted(ids), "every job claimed exactly once"


def test_interrupted_too_often_fails(tmp_path):
    _, engine = sandbox(tmp_path)
    job_id, _ = queue.enqueue(engine, "probe", {}, max_attempts=2)
    for _ in range(2):
        queue.claim(engine, "w")
        queue.requeue_interrupted(engine)  # as a restart after a crash would
    row = job(engine, job_id)
    assert row.status == "failed" and row.error == "interrupted 2 times; not retried again"


def test_the_job_process_uses_the_worker_settings(tmp_path, monkeypatch):
    # The environment names another data root: the job must still run against the worker's (the base bake's case).
    settings, engine = sandbox(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setenv("LAMINARIO_DATA_ROOT", str(elsewhere))
    job_id, public_id = queue.enqueue(engine, "probe", {"steps": 1, "seconds": 0})
    Worker(settings).run(max_jobs=1)
    row = job(engine, job_id)
    assert row.status == "succeeded", row.error
    assert (settings.data_root / "probes" / f"{public_id}.txt").exists()
    assert not elsewhere.exists()


def test_unknown_kind_fails_cleanly(tmp_path, monkeypatch):
    settings, engine = sandbox(tmp_path, monkeypatch)
    job_id, _ = queue.enqueue(engine, "no_such_kind", {})
    Worker(settings).run(max_jobs=1)
    assert job(engine, job_id).error == "unknown job kind 'no_such_kind'"


def test_a_job_that_fails_unreadably_does_not_stop_the_worker(tmp_path, monkeypatch):
    """A job's error that cannot be pickled back to the worker broke pebble's pool, and every job after it failed to
    start: the base bake stopped at a DICOM archive. The error now travels as text, and a failed pool is replaced."""
    settings, engine = sandbox(tmp_path, monkeypatch)
    unreadable, _ = queue.enqueue(engine, "probe", {"fail": "unpicklable"})
    plain, _ = queue.enqueue(engine, "probe", {"fail": "error"})
    fine, _ = queue.enqueue(engine, "probe", {"steps": 1, "seconds": 0.1})
    assert Worker(settings).run(max_jobs=3) == 3
    first = job(engine, unreadable)
    assert first.status == "failed" and first.error.startswith("app.jobs.kinds.JobError: _Unpicklable")
    second = job(engine, plain)
    assert second.status == "failed" and "ValueError: the probe was asked to fail" in second.error
    assert job(engine, fine).status == "succeeded"
