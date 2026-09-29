"""Helpers for the account tests: an app on a sandbox database, accounts of every role, signed-in requests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from app.accounts.__main__ import invite
from app.accounts.users import COOKIE_NAME
from app.config import Settings
from app.db.migrate import upgrade_to_head
from app.main import create_app

PASSWORD = "correct horse battery staple"
ORIGIN = "https://laminario.example.org"


def settings_for(tmp_path: Path, **overrides) -> Settings:
    values = {"public_base_url": ORIGIN, "data_root": tmp_path / "data", "secret_key": "test-secret-" + "x" * 40}
    settings = Settings(**(values | overrides))
    upgrade_to_head(settings.data_root / "laminario.sqlite3")
    return settings


def token_of(link: str) -> str:
    return parse_qs(urlsplit(link).query)["token"][0]


def cli_invitation(settings: Settings, role: str = "admin", email: str | None = None) -> str:
    return token_of(asyncio.run(invite(settings, role, email, "test")))


def register(client: TestClient, token: str, email: str, password: str = PASSWORD, name: str = "Test Person"):
    return client.post("/api/auth/register", json={"token": token, "email": email, "password": password,
                                                   "display_name": name})


def sign_in(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    """Headers carrying the session cookie of ``email`` (the client's own cookie jar is left empty)."""
    response = client.post("/api/auth/login", data={"username": email, "password": password})
    assert response.status_code == 204, response.text
    value = response.cookies.get(COOKIE_NAME)
    client.cookies.clear()
    return {"Cookie": f"{COOKIE_NAME}={value}"}


def account(client: TestClient, settings: Settings, role: str, email: str, issuer: dict | None = None) -> dict:
    """An account of ``role``: invited by ``issuer`` (headers of an admin) or from the command line."""
    if issuer is None:
        token = cli_invitation(settings, role)
    else:
        created = client.post("/api/invitations", json={"role": role}, headers=issuer)
        assert created.status_code == 201, created.text
        token = token_of(created.json()["link"])
    assert register(client, token, email).status_code == 201
    return sign_in(client, email)


def app_client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
