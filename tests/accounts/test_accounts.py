"""Invitation-only registration, and the optional mail sender against a local SMTP sink."""

from __future__ import annotations

import datetime as dt
import email
import ssl
import threading
from email import policy

import pytest
from sqlalchemy import create_engine, text

from app.db.base import utcnow
from tests.delivery.support import free_port

from .support import (
    ORIGIN, PASSWORD, account, app_client, cli_invitation, register, settings_for, sign_in, token_of,
)


def db(settings):
    return create_engine(f"sqlite:///{(settings.data_root / 'laminario.sqlite3').as_posix()}")


# R-050
def test_registration_requires_invitation(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        assert client.post("/api/auth/register", json={"email": "a@example.org", "password": PASSWORD,
                                                       "display_name": "A"}).status_code == 422, "no token, no account"
        assert register(client, "x" * 43, "a@example.org").status_code == 400, "an unknown token"

        admin = account(client, settings, "admin", "admin@example.org")
        me = client.get("/api/users/me", headers=admin).json()
        assert (me["role"], me["is_superuser"]) == ("admin", True)

        # used: a link works once
        token = token_of(client.post("/api/invitations", json={"role": "contributor"}, headers=admin).json()["link"])
        assert register(client, token, "b@example.org").status_code == 201
        assert register(client, token, "c@example.org").status_code == 400

        # revoked
        created = client.post("/api/invitations", json={"role": "contributor"}, headers=admin).json()
        assert client.delete(f"/api/invitations/{created['id']}", headers=admin).status_code == 204
        assert register(client, token_of(created["link"]), "d@example.org").status_code == 400

        # expired
        created = client.post("/api/invitations", json={"role": "contributor"}, headers=admin).json()
        with db(settings).begin() as conn:
            conn.execute(text("UPDATE invitation SET expires_at = :past WHERE id = :id"),
                         {"past": (utcnow() - dt.timedelta(minutes=1)).isoformat(sep=" "), "id": created["id"]})
        assert register(client, token_of(created["link"]), "e@example.org").status_code == 400

        # bound to an address: another address is refused and the link stays usable for the right one
        created = client.post("/api/invitations", json={"role": "identifier", "email": "f@example.org"},
                              headers=admin).json()
        assert register(client, token_of(created["link"]), "g@example.org").status_code == 400
        weak = register(client, token_of(created["link"]), "f@example.org", password="short")
        assert weak.status_code == 400 and "12 characters" in weak.json()["detail"]
        made = register(client, token_of(created["link"]), "F@Example.org")
        assert made.status_code == 201 and made.json()["role"] == "identifier"

        statuses = {i["id"]: i["status"] for i in client.get("/api/invitations", headers=admin).json()}
        assert sorted(statuses.values()) == ["expired", "revoked", "used", "used", "used"]  # with the admin's own

    with db(settings).connect() as conn:
        stored = conn.execute(text("SELECT token_sha256 FROM invitation")).scalars().all()
    assert all(len(value) == 64 for value in stored), "only digests of tokens are stored"


def test_one_link_one_account_under_a_race(tmp_path):
    settings = settings_for(tmp_path)
    token = cli_invitation(settings, "contributor")
    results: list[int] = []
    with app_client(settings) as client:
        threads = [threading.Thread(target=lambda i=i: results.append(register(client, token, f"r{i}@example.org")
                                                                          .status_code)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
    assert sorted(results) == [201, 400, 400, 400, 400, 400]


def test_no_open_registration_route(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        schema = client.get("/api/openapi.json").json()
    register_body = schema["paths"]["/api/auth/register"]["post"]["requestBody"]["content"]["application/json"]
    assert "Registration" in str(register_body), "the only registration route is the invitation one"


# --- the mail sender ----------------------------------------------------------------------------------------


def certificate(folder):
    """A self-signed certificate for 127.0.0.1, standing in for the relay's."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    import ipaddress

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(minutes=5))
            .not_valid_after(now + dt.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
            .sign(key, hashes.SHA256()))
    cert_path, key_path = folder / "relay.pem", folder / "relay.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    return cert_path, key_path


@pytest.fixture
def smtp_sink(tmp_path):
    """A local SMTP server that requires STARTTLS and keeps every message it receives."""
    from aiosmtpd.controller import Controller

    received: list[email.message.EmailMessage] = []

    class Handler:
        async def handle_DATA(self, server, session, envelope):  # noqa: N802 (aiosmtpd's name)
            received.append(email.message_from_bytes(envelope.content, policy=policy.default))
            return "250 OK"

    cert_path, key_path = certificate(tmp_path)
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(cert_path, key_path)
    port = free_port()  # aiosmtpd connects to its own port to start, so it cannot take port 0
    controller = Controller(Handler(), hostname="127.0.0.1", port=port, tls_context=context, require_starttls=True)
    controller.start()
    try:
        yield {"port": port, "cafile": cert_path, "received": received}
    finally:
        controller.stop()


# R-051
def test_mail_adapter_against_local_sink(tmp_path, smtp_sink):
    mailing = settings_for(tmp_path / "with-mail", smtp_host="127.0.0.1", smtp_port=smtp_sink["port"],
                           smtp_sender="Laminario <no-reply@laminario.example.org>", smtp_cafile=smtp_sink["cafile"])
    received = smtp_sink["received"]
    with app_client(mailing) as client:
        admin = account(client, mailing, "admin", "admin@example.org")
        answer = client.post("/api/invitations", json={"role": "contributor", "email": "new@example.org"},
                             headers=admin).json()
        assert answer["mailed"] is True and answer["link"] is None, "a mailed link is not shown to anyone"
        assert len(received) == 1
        invitation_mail = received[0]
        assert invitation_mail["To"] == "new@example.org"
        assert invitation_mail["From"] == "Laminario <no-reply@laminario.example.org>"
        body = invitation_mail.get_content()
        link = next(word for word in body.split() if word.startswith(f"{ORIGIN}/join?token="))
        assert register(client, token_of(link), "new@example.org").status_code == 201, "the mailed link works"

        assert client.post("/api/auth/forgot-password", json={"email": "new@example.org"}).status_code == 202
        assert len(received) == 2 and "Reset your Laminario password" in received[1]["Subject"]
        reset = next(w for w in received[1].get_content().split() if w.startswith(f"{ORIGIN}/reset-password?token="))
        changed = client.post("/api/auth/reset-password",
                              json={"token": token_of(reset), "password": "a new one, long"})
        assert changed.status_code == 200
        sign_in(client, "new@example.org", "a new one, long")

    silent = settings_for(tmp_path / "without-mail")
    with app_client(silent) as client:
        admin = account(client, silent, "admin", "admin@example.org")
        answer = client.post("/api/invitations", json={"role": "contributor", "email": "other@example.org"},
                             headers=admin).json()
        assert answer["mailed"] is False and answer["link"].startswith(f"{ORIGIN}/join?token=")
        assert client.get("/api/invitations", headers=admin).json()[0]["link"] is None, "shown once, never again"
        assert register(client, token_of(answer["link"]), "other@example.org").status_code == 201
        other = sign_in(client, "other@example.org")
        assert client.post("/api/auth/forgot-password", json={"email": "other@example.org"}).status_code == 202
        target = client.get("/api/users/me", headers=other).json()["id"]
        assert client.post(f"/api/admin/accounts/{target}/reset-link", headers=other).status_code == 403
        issued = client.post(f"/api/admin/accounts/{target}/reset-link", headers=admin).json()
        assert issued["link"].startswith(f"{ORIGIN}/reset-password?token=") and issued["expires_in_minutes"] == 60
        reset = client.post("/api/auth/reset-password",
                            json={"token": token_of(issued["link"]), "password": "fresh and long passphrase"})
        assert reset.status_code == 200
        sign_in(client, "other@example.org", "fresh and long passphrase")
    assert len(received) == 2, "nothing was mailed without a sender"
