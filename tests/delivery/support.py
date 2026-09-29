"""Shared helpers for the delivery tests: seeded slides, a local HTTP server, the pinned IIIF schema, containers."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from sqlalchemy import delete

from app.config import Settings
from app.contracts.ingest import SlideCaseSubmission
from app.db.base import utcnow
from app.db.engine import async_sessions, make_async_engine
from app.db.migrate import upgrade_to_head
from app.db.models import Asset
from app.services import slides
from tests import payloads

IIPSRV_IMAGE = "iipsrv/iipsrv@sha256:a1ce6fe828afc91893a03b41b360a50d84f905a96b410391ce4f8be636577353"
NGINX_IMAGE = "nginx@sha256:77e5d4a6ad906c5d3793764085706577fa705b1dc6f244ea0241c4b5e2155385"  # 1.24.0-alpine

# The IIIF Presentation 3 JSON Schema of the IIIF validator, pinned by commit and by git blob hash. The
# repository states no licence, so the file is fetched and cached, not committed.
IIIF_SCHEMA_URL = ("https://raw.githubusercontent.com/IIIF/presentation-validator/"
                   "455c3c325b49e61ac6c393c385d9478e68ce42bd/schema/iiif_3_0.json")
IIIF_SCHEMA_BLOB = "c1bdef77ab5de38aa9a6d5e69d76ab554b05935b"


def make_settings(tmp_path: Path, **overrides) -> Settings:
    values = {"public_base_url": "https://laminario.example.org", "data_root": tmp_path / "data"} | overrides
    return Settings(**values)


def seed_slide(settings: Settings, assets: list[dict], *, publish: bool = True, geoprivacy: str = "open",
               origin: str = "contribution") -> str:
    """A slide from the standard contribution, its assets replaced by ``assets`` (fields of ``Asset``)."""
    database = settings.data_root / "laminario.sqlite3"
    upgrade_to_head(database)

    async def run() -> str:
        engine = make_async_engine(database)
        try:
            async with async_sessions(engine)() as session:
                payload = payloads.contribution()
                payload["specimen"]["geoprivacy"] = geoprivacy
                slide = await slides.create_slide(session, SlideCaseSubmission.model_validate(payload),
                                                  contributor_id="user-1")
                await session.execute(delete(Asset).where(Asset.slide_id == slide.id))
                for order, spec in enumerate(assets):
                    fields = {"status": "ready", "sort_order": order, "role": "single"} | spec
                    session.add(Asset(slide_id=slide.id, **fields))
                slide.origin = origin
                if publish:
                    slide.status = "published"
                    slide.published_at = utcnow()
                await session.commit()
                return slide.short_id
        finally:
            await engine.dispose()

    return asyncio.run(run())


def free_port(host: str = "127.0.0.1") -> int:
    with socket.socket() as s:
        s.bind((host, 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def serve(routes: dict[str, tuple[int, dict, bytes]]):
    """A local HTTP server answering GET for exact paths: path -> (status, headers, body). Yields its base URL."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (the standard library's name)
            status, headers, body = routes.get(self.path.split("?")[0], (404, {}, b"not found"))
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


def json_body(document: dict) -> bytes:
    return json.dumps(document).encode("utf-8")


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def iiif_schema(cache_dir: Path) -> dict:
    """The pinned schema: from the fixture vault or the cache, else downloaded; skipped when unreachable."""
    candidates = []
    fixtures = os.environ.get("LAMINARIO_FIXTURES") or Settings().fixtures
    if fixtures:
        candidates.append(Path(fixtures) / "iiif" / "iiif_3_0.json")
    candidates.append(cache_dir / "iiif_3_0.json")
    for path in candidates:
        if path.is_file() and git_blob_sha1(path.read_bytes()) == IIIF_SCHEMA_BLOB:
            return json.loads(path.read_bytes())
    import httpx2

    try:
        data = httpx2.get(IIIF_SCHEMA_URL, timeout=30.0, follow_redirects=True).content
    except httpx2.HTTPError as exc:
        pytest.skip(f"the pinned IIIF schema is not cached and could not be fetched: {exc}")
    if git_blob_sha1(data) != IIIF_SCHEMA_BLOB:
        pytest.fail("the fetched IIIF schema does not match its pinned hash")
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "iiif_3_0.json").write_bytes(data)
    return json.loads(data)


def docker() -> str:
    """The docker CLI with a reachable engine, or the test is skipped."""
    exe = shutil.which("docker")
    if not exe:
        pytest.skip("no docker CLI on this machine")
    probe = subprocess.run([exe, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True,
                           timeout=30)
    if probe.returncode != 0:
        pytest.skip("the docker engine is not reachable")
    return exe


def wait_for_http(url: str, seconds: float = 30.0, expect: int | None = None) -> None:
    """Until ``url`` answers (with status ``expect`` when given), or raise after ``seconds``."""
    import httpx2

    deadline = time.monotonic() + seconds
    last = "no answer"
    while time.monotonic() < deadline:
        try:
            status = httpx2.get(url, timeout=2.0).status_code
            if expect is None or status == expect:
                return
            last = f"HTTP {status}"
        except httpx2.HTTPError as exc:
            last = type(exc).__name__
        time.sleep(0.5)
    raise TimeoutError(f"{url} did not answer as expected within {seconds:g} s (last: {last})")


@contextlib.contextmanager
def container(args: list[str], name: str):
    """``docker run -d --rm --name <name> <args>``, always stopped on exit."""
    exe = docker()
    run = subprocess.run([exe, "run", "-d", "--rm", "--name", name, *args], capture_output=True, text=True,
                         timeout=300)
    if run.returncode != 0:
        raise RuntimeError(f"docker run failed: {run.stderr.strip()}")
    try:
        yield name
    finally:
        subprocess.run([exe, "stop", "-t", "5", name], capture_output=True, timeout=60)


COMPOSE_FILE = Path(__file__).resolve().parents[2] / "deploy" / "iipsrv" / "compose.yaml"


@contextlib.contextmanager
def iipsrv_stack(store: Path, port: int, project: str):
    """The production compose file of the tile server, on a sandbox store and a free port; always taken down."""
    exe = docker()
    env = os.environ | {"LAMINARIO_STORE": str(store), "LAMINARIO_IIPSRV_PORT": str(port)}
    base = [exe, "compose", "-f", str(COMPOSE_FILE), "-p", project]
    up = subprocess.run([*base, "up", "-d"], capture_output=True, text=True, env=env, timeout=300)
    if up.returncode != 0:
        raise RuntimeError(f"docker compose up failed: {up.stderr.strip()}")
    try:
        yield f"{project}-iipsrv-1"
    finally:
        subprocess.run([*base, "down"], capture_output=True, env=env, timeout=120)
