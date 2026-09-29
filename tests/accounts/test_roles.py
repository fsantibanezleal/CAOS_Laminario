"""Roles, walked over every capability and over the routes that exist."""

from __future__ import annotations

import copy

from app.accounts import roles
from tests import payloads

from .support import ORIGIN, account, app_client, settings_for

# The design document's sentence, as a table: visitor reads, contributor submits and annotates (U11), identifier
# identifies, curator moderates and overrides placement, admin manages invitations (and accounts). Each role includes
# the ones below.
EXPECTED = {
    None:          {"read"},
    "contributor": {"read", "submit", "annotate"},
    "identifier":  {"read", "submit", "annotate", "identify"},
    "curator":     {"read", "submit", "annotate", "identify", "moderate", "override_placement", "invite"},
    "admin":       set(roles.CAPABILITIES),
}


def case(override: bool = False) -> dict:
    payload = copy.deepcopy(payloads.contribution())
    if override:
        payload["placement"]["override_reason"] = "the rule does not cover this host association yet"
    return payload


# R-052
def test_role_matrix(tmp_path):
    for role, capabilities in EXPECTED.items():
        for capability in roles.CAPABILITIES:
            assert roles.allowed(role, capability) == (capability in capabilities), (role, capability)

    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        admin = account(client, settings, "admin", "admin@example.org")
        people = {"admin": admin}
        for role in ("contributor", "identifier", "curator"):
            people[role] = account(client, settings, role, f"{role}@example.org", issuer=admin)
        people[None] = {}

        for role, headers in people.items():
            assert client.get("/api/slides", headers=headers).status_code == 200, "everyone reads"
            created = client.post("/api/slide-cases", json=case(), headers=headers)
            assert created.status_code == (401 if role is None else 201), (role, created.text)
            override = client.post("/api/slide-cases", json=case(override=True), headers=headers)
            assert override.status_code == {None: 401, "contributor": 403, "identifier": 403}.get(role, 201), role
            invited = client.post("/api/invitations", json={"role": "contributor"}, headers=headers)
            assert invited.status_code == {None: 401, "contributor": 403, "identifier": 403}.get(role, 201), role
            senior = client.post("/api/invitations", json={"role": "curator"}, headers=headers)
            assert senior.status_code == {None: 401, "admin": 201}.get(role, 403), role
            listed = client.get("/api/invitations", headers=headers)
            assert listed.status_code == {None: 401, "contributor": 403, "identifier": 403}.get(role, 200), role

        target = client.get("/api/users/me", headers=people["contributor"]).json()["id"]
        for role, headers in people.items():
            promote = client.patch(f"/api/admin/accounts/{target}/role", json={"role": "identifier"},
                                   headers=headers)
            assert promote.status_code == {None: 401, "admin": 200}.get(role, 403), role
            link = client.post(f"/api/admin/accounts/{target}/reset-link", headers=headers)
            assert link.status_code == {None: 401, "admin": 200}.get(role, 403), role

        # a curator sees only the invitations it issued; an admin sees all
        curator_view = client.get("/api/invitations", headers=people["curator"]).json()
        admin_view = client.get("/api/invitations", headers=admin).json()
        assert len(curator_view) == 1 and len(admin_view) > len(curator_view)

        # an account cannot raise its own role
        me = client.patch("/api/users/me", json={"role": "admin", "display_name": "Renamed"},
                          headers=people["identifier"])
        assert me.status_code == 200 and me.json()["role"] == "identifier" and me.json()["display_name"] == "Renamed"

        # the last admin keeps the role
        own = client.get("/api/users/me", headers=admin).json()["id"]
        assert client.patch(f"/api/admin/accounts/{own}/role", json={"role": "curator"},
                            headers=admin).status_code == 409


def test_cross_site_writes_are_refused(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        admin = account(client, settings, "admin", "admin@example.org")
        hostile = client.post("/api/invitations", json={"role": "admin"},
                              headers=admin | {"Origin": "https://evil.example"})
        assert hostile.status_code == 403 and hostile.json()["detail"] == "cross-site request refused"
        same = client.post("/api/invitations", json={"role": "contributor"}, headers=admin | {"Origin": ORIGIN})
        assert same.status_code == 201
        assert client.get("/api/slides", headers={"Origin": "https://evil.example"}).status_code == 200, \
            "reads stay open to any origin"


def test_sessions_end_at_sign_out(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        admin = account(client, settings, "admin", "admin@example.org")
        assert client.get("/api/users/me", headers=admin).status_code == 200
        assert client.post("/api/auth/logout", headers=admin).status_code == 204
        assert client.get("/api/users/me", headers=admin).status_code == 401, "the session row is gone"
        wrong = client.post("/api/auth/login", data={"username": "admin@example.org", "password": "wrong password!"})
        assert wrong.status_code == 400
