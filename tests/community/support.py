"""Helpers for the community tests: accounts of every role and published contributions, offline (the GBIF answers
are the recorded ones, ``tests/collections/gbif``)."""

from __future__ import annotations

import copy

from sqlalchemy import text

from app.db.engine import database_path, make_sync_engine
from app.services import cases
from tests import payloads
from tests.accounts.support import account

POLYPLAX_BOREALIS = {"kind": "taxon", "ref": "1032608", "name": "Polyplax borealis", "rank": "species"}
POLYPLAX_ALASKENSIS = {"kind": "taxon", "ref": "1032575", "name": "Polyplax alaskensis", "rank": "species"}
POLYPLAX = {"kind": "taxon", "ref": "1032563", "name": "Polyplax", "rank": "genus"}
POLYPLACIDAE = {"kind": "taxon", "ref": "4369", "name": "Polyplacidae", "rank": "family"}
HOMO_SAPIENS = {"kind": "taxon", "ref": "2436436", "name": "Homo sapiens", "rank": "species"}


def sql(settings, statement: str, **params):
    engine = make_sync_engine(database_path(settings))
    try:
        with engine.begin() as conn:
            result = conn.execute(text(statement), params)
            return result.all() if result.returns_rows else None
    finally:
        engine.dispose()


def people(client, settings) -> dict[str, dict]:
    """An admin, two curators, a contributor and three identifiers, each as signed-in headers."""
    admin = account(client, settings, "admin", "admin@example.org")
    out = {"admin": admin}
    for role, email in (("curator", "curator@example.org"), ("curator", "curator2@example.org"),
                        ("contributor", "maker@example.org"), ("identifier", "one@example.org"),
                        ("identifier", "two@example.org"), ("identifier", "three@example.org")):
        out[email.split("@")[0]] = account(client, settings, role, email, issuer=admin)
    return out


def published(client, settings, contributor: dict, **specimen) -> str:
    """A contribution taken through the lifecycle to publication; returns its short id."""
    payload = copy.deepcopy(payloads.contribution())
    payload["specimen"].update(specimen)
    created = client.post("/api/slide-cases", json=payload, headers=contributor)
    assert created.status_code == 201, created.text
    sid = created.json()["id"]
    for asset_id, slide_id in sql(settings, "SELECT a.id, a.slide_id FROM asset a JOIN slide s ON s.id = a.slide_id "
                                            "WHERE s.short_id = :s", s=sid):
        sql(settings, "INSERT INTO upload (tus_id, user_id, slide_id, asset_id, size, wsi, status, created_at) "
                      "SELECT :t, contributor_id, :s, :a, 10, 0, 'accepted', CURRENT_TIMESTAMP "
                      "FROM slide WHERE id = :s", t=f"tus-{asset_id}", s=slide_id, a=asset_id)
    assert client.post(f"/api/slide-cases/{sid}/submit", headers=contributor).status_code == 200
    engine = make_sync_engine(database_path(settings))
    try:
        ids = [r.id for r in sql(settings, "SELECT a.id FROM asset a JOIN slide s ON s.id = a.slide_id "
                                           "WHERE s.short_id = :s", s=sid)]
        for asset_id in ids:
            sql(settings, "UPDATE asset SET status = 'ready' WHERE id = :a", a=asset_id)
            cases.after_job(engine, "process_asset", {"asset_id": asset_id}, False, None)
    finally:
        engine.dispose()
    assert client.get(f"/api/slides/{sid}").status_code == 200
    return sid


def identify(client, sid: str, who: dict, anchor: dict, **extra):
    return client.post(f"/api/slides/{sid}/identifications", json={"anchor": anchor, **extra}, headers=who)


def community(client, sid: str, who: dict | None = None) -> dict:
    answer = client.get(f"/api/slides/{sid}/identifications", headers=who or {})
    assert answer.status_code == 200, answer.text
    return answer.json()
