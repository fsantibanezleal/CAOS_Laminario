"""Helpers for the worker tests: a database under a sandbox, the worker as a real process, a hard kill."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import text

from app.config import Settings
from app.db.engine import database_path, make_sync_engine
from app.db.migrate import upgrade_to_head
from app.jobs import journal

ROOT = Path(__file__).resolve().parents[2]


def sandbox(tmp_path: Path, monkeypatch=None) -> tuple[Settings, object]:
    """Settings and an engine on a fresh database under ``tmp_path``; the environment points children there."""
    data_root = tmp_path / "data"
    if monkeypatch is not None:
        monkeypatch.setenv("LAMINARIO_DATA_ROOT", str(data_root))
    settings = Settings(data_root=data_root)
    upgrade_to_head(database_path(settings))
    return settings, make_sync_engine(database_path(settings))


def start_worker(settings: Settings, log: Path) -> subprocess.Popen:
    """``python -m app.worker`` in its own process group, so the whole tree can be killed at once."""
    env = os.environ | {"LAMINARIO_DATA_ROOT": str(settings.data_root)}
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    handle = open(log, "ab")
    return subprocess.Popen([sys.executable, "-m", "app.worker"], cwd=ROOT, env=env, stdout=handle,
                            stderr=subprocess.STDOUT, **kwargs)


def kill_tree(process: subprocess.Popen) -> None:
    """Kill the worker and every process it started, without warning: a crash, not a stop."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=60)
    else:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    process.wait(timeout=30)


def stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        kill_tree(process)


def pid_alive(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=30)
        return str(pid) in out.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def job(engine, job_id: int):
    with engine.connect() as conn:
        return conn.execute(text("SELECT * FROM job WHERE id = :id"), {"id": job_id}).one()


def events(engine, job_id: int) -> list[journal.Event]:
    with engine.connect() as conn:
        return journal.after(conn, job_id, 0)


def wait_until(predicate, seconds: float, what: str) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.2)
    raise TimeoutError(f"{what} did not happen within {seconds:g} s")
