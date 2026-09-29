"""GET /api/session: the signed-in account, or null for a visitor, a 200 either way."""

from __future__ import annotations

from .support import account, app_client, settings_for


def test_the_session_names_the_account_or_nobody(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        visitor = client.get("/api/session")
        assert visitor.status_code == 200 and visitor.json() is None
        admin = account(client, settings, "admin", "admin@example.org")
        signed = client.get("/api/session", headers=admin)
        assert signed.status_code == 200
        assert signed.json()["email"] == "admin@example.org" and signed.json()["role"] == "admin"
