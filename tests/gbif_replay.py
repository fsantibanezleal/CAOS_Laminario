"""A local stand-in for the GBIF API: it replays answers recorded from the real service.

The tests never call GBIF. ``tests/collections/record_gbif.py`` saved real answers in ``tests/collections/gbif``;
this server returns them for the same paths (``/v1/species/{key}``, ``/v1/species/{key}/parents``,
``/v1/species/suggest?q=``) and answers 404 for anything it has no record of, as GBIF does for an unknown key.
``conftest.py`` starts one for the whole session and points ``LAMINARIO_GBIF_API_URL`` at it.
"""

from __future__ import annotations

import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

RECORDS = Path(__file__).resolve().parent / "collections" / "gbif"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (the stdlib's name)
        url = urlsplit(self.path)
        name = None
        if m := re.fullmatch(r"/v1/species/(\d+)", url.path):
            name = f"species-{m.group(1)}.json"
        elif m := re.fullmatch(r"/v1/species/(\d+)/parents", url.path):
            name = f"parents-{m.group(1)}.json"
        elif url.path == "/v1/species/suggest":
            q = (parse_qs(url.query).get("q") or [""])[0].lower()
            name = f"suggest-{q}.json"
        record = RECORDS / name if name else None
        if record is None or not record.exists():
            self.send_response(404)
            self.end_headers()
            return
        body = record.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


class Replay:
    def __init__(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}/v1"

    def start(self) -> Replay:
        self.thread.start()
        return self

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
