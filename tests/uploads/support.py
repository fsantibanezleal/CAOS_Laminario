"""A real upload path for the tests: the API served by uvicorn, tusd calling its hooks, a small tus client.

tusd is the binary named by ``LAMINARIO_TUSD_BIN`` (v2.10.1; the tests are skipped without it). It runs with the same
flags as ``deploy/tusd/compose.yaml``, on free loopback ports, writing to the sandbox's quarantine.
"""

from __future__ import annotations

import base64
import contextlib
import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx2
import pytest

from app.config import Settings
from app.db.migrate import upgrade_to_head
from app.main import create_app
from tests.accounts.support import PASSWORD, cli_invitation
from tests.delivery.support import free_port, wait_for_http

TUS = {"Tus-Resumable": "1.0.0"}


def tusd_binary() -> Path:
    value = os.environ.get("LAMINARIO_TUSD_BIN") or Settings().tusd_bin
    if not value or not Path(value).is_file():
        pytest.skip("LAMINARIO_TUSD_BIN does not name the tusd binary; the upload tests need it")
    return Path(value)


def settings_for(tmp_path: Path, **overrides) -> Settings:
    values = {"data_root": tmp_path / "data", "secret_key": "test-secret-" + "y" * 40} | overrides
    settings = Settings(**values)
    upgrade_to_head(settings.data_root / "laminario.sqlite3")
    settings.quarantine_root.mkdir(parents=True, exist_ok=True)
    return settings


@contextlib.contextmanager
def upload_stack(settings: Settings):
    """The API (uvicorn, in a thread) and tusd (a process) wired together; both stopped on exit."""
    import uvicorn

    binary = tusd_binary()
    api_port, tus_port = free_port(), free_port()
    settings = settings.model_copy(update={"public_base_url": f"http://127.0.0.1:{api_port}"})
    server = uvicorn.Server(uvicorn.Config(create_app(settings), host="127.0.0.1", port=api_port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    process = None
    try:
        wait_for_http(f"http://127.0.0.1:{api_port}/api/health", expect=200)
        process = subprocess.Popen(
            [str(binary), "-host=127.0.0.1", f"-port={tus_port}", "-base-path=/files/",
             f"-upload-dir={settings.quarantine_root}",
             f"-hooks-http=http://127.0.0.1:{api_port}/api/_internal/tus-hook",
             "-hooks-http-forward-headers=Cookie", "-hooks-enabled-events=pre-create,post-finish,post-terminate",
             "-disable-download", "-disable-cors", f"-max-size={settings.max_upload_bytes}",
             "-show-greeting=false"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_for_http(f"http://127.0.0.1:{tus_port}/files/")
        yield {"api": f"http://127.0.0.1:{api_port}", "tus": f"http://127.0.0.1:{tus_port}/files/",
               "settings": settings}
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
        server.should_exit = True
        thread.join(10)


def contributor(stack: dict, email: str = "maker@example.org") -> tuple[dict, str, list[int]]:
    """A contributor (invited from the command line), signed in, with one draft case; its cookie and asset ids."""
    from tests import payloads

    token = cli_invitation(stack["settings"], "contributor")
    with httpx2.Client(base_url=stack["api"]) as api:
        assert api.post("/api/auth/register", json={"token": token, "email": email, "password": PASSWORD,
                                                    "display_name": "Maker"}).status_code == 201
        login = api.post("/api/auth/login", data={"username": email, "password": PASSWORD})
        assert login.status_code == 204
        cookie = {"Cookie": f"laminario_session={login.cookies['laminario_session']}"}
        created = api.post("/api/slide-cases", json=payloads.contribution(), headers=cookie)
        assert created.status_code == 201, created.text
        slide = created.json()["id"]
    from sqlalchemy import create_engine, text

    engine = create_engine(f"sqlite:///{(stack['settings'].data_root / 'laminario.sqlite3').as_posix()}")
    with engine.connect() as conn:
        assets = [r.id for r in conn.execute(text(
            "SELECT a.id FROM asset a JOIN slide s ON s.id = a.slide_id WHERE s.short_id = :s ORDER BY a.id"),
            {"s": slide})]
    engine.dispose()
    return cookie, slide, assets


def metadata(**values: str) -> str:
    return ",".join(f"{k} {base64.b64encode(v.encode()).decode()}" for k, v in values.items())


def create(stack: dict, size: int, headers: dict, **meta: str) -> httpx2.Response:
    return httpx2.post(stack["tus"], headers=TUS | headers | {"Upload-Length": str(size),
                                                             "Upload-Metadata": metadata(**meta)}, timeout=30)


def offset(location: str, headers: dict) -> int:
    return int(httpx2.head(location, headers=TUS | headers, timeout=30).headers["Upload-Offset"])


def patch(location: str, start: int, data: bytes, headers: dict) -> httpx2.Response:
    return httpx2.patch(location, content=data, timeout=120,
                        headers=TUS | headers | {"Upload-Offset": str(start),
                                                 "Content-Type": "application/offset+octet-stream"})


def interrupted_patch(location: str, start: int, data: bytes, headers: dict, send: int) -> None:
    """Announce all of ``data`` but send only ``send`` bytes, then drop the connection: a lost network."""
    parts = urlsplit(location)
    with socket.create_connection((parts.hostname, parts.port), timeout=30) as raw:
        lines = [f"PATCH {parts.path} HTTP/1.1", f"Host: {parts.netloc}", "Tus-Resumable: 1.0.0",
                 f"Upload-Offset: {start}", "Content-Type: application/offset+octet-stream",
                 f"Content-Length: {len(data)}"] + [f"{k}: {v}" for k, v in headers.items()]
        raw.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("ascii"))
        raw.sendall(data[:send])
        time.sleep(0.5)
    time.sleep(1.0)  # tusd notices the closed connection and saves what arrived


TUS_IMAGE = "tusproject/tusd@sha256:7b1c552a8b42f4b36cb01f2a3bd49f82ab078b2eefd191459e716141dd50376c"
COMPOSE_FILE = Path(__file__).resolve().parents[2] / "deploy" / "tusd" / "compose.yaml"


@contextlib.contextmanager
def compose_tusd(quarantine: Path, port: int, api_port: int, project: str):
    """The production compose file of tusd on a sandbox quarantine and free ports; always taken down."""
    from tests.delivery.support import docker

    exe = docker()
    env = os.environ | {"LAMINARIO_QUARANTINE": str(quarantine), "LAMINARIO_TUSD_PORT": str(port),
                        "LAMINARIO_API_PORT": str(api_port), "LAMINARIO_UID": str(os.getuid()),
                        "LAMINARIO_GID": str(os.getgid())}
    base = [exe, "compose", "-f", str(COMPOSE_FILE), "-p", project]
    up = subprocess.run([*base, "up", "-d"], capture_output=True, text=True, env=env, timeout=300)
    if up.returncode != 0:
        raise RuntimeError(f"docker compose up failed: {up.stderr.strip()}")
    try:
        yield f"{project}-tusd-1"
    finally:
        subprocess.run([*base, "down"], capture_output=True, env=env, timeout=120)
