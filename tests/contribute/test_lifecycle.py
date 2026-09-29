"""R-1205 and R-1206: a contribution goes draft, processing, published; an image that fails sends it back to draft
with the reason; a contributor lists, reopens, changes and deletes their own drafts and nobody else's."""

from __future__ import annotations

import copy

from sqlalchemy import text

from app.db.engine import database_path, make_sync_engine
from app.services import cases
from tests import payloads
from tests.accounts.support import account, app_client, settings_for


def contribution(**slide) -> dict:
    payload = copy.deepcopy(payloads.contribution())
    payload["slide"].update(slide)
    return payload


def sql(settings, statement: str, **params):
    engine = make_sync_engine(database_path(settings))
    try:
        with engine.begin() as conn:
            result = conn.execute(text(statement), params)
            return result.all() if result.returns_rows else None
    finally:
        engine.dispose()


def give_files(settings, short_id: str) -> None:
    """Every image of a case receives an accepted upload, as the verification leaves it."""
    for (asset_id, slide_id) in sql(settings, "SELECT a.id, a.slide_id FROM asset a JOIN slide s ON s.id = a.slide_id "
                                              "WHERE s.short_id = :s", s=short_id):
        sql(settings, "INSERT INTO upload (tus_id, user_id, slide_id, asset_id, size, wsi, status, created_at) "
                      "SELECT :t, contributor_id, :s, :a, 10, 0, 'accepted', CURRENT_TIMESTAMP "
                      "FROM slide WHERE id = :s",
            t=f"tus-{asset_id}", s=slide_id, a=asset_id)


def test_a_case_from_draft_to_published_and_back(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        admin = account(client, settings, "admin", "admin@example.org")
        maker = account(client, settings, "contributor", "maker@example.org", issuer=admin)
        other = account(client, settings, "contributor", "other@example.org", issuer=admin)

        created = client.post("/api/slide-cases", json=contribution(), headers=maker)
        assert created.status_code == 201, created.text
        sid = created.json()["id"]

        # Listed and reopened by its contributor, unknown to anyone else.
        mine = client.get("/api/slide-cases", headers=maker).json()
        assert [c["id"] for c in mine] == [sid] and mine[0]["status"] == "draft"
        assert [i["has_file"] for i in mine[0]["images"]] == [False, False]
        record = client.get(f"/api/slide-cases/{sid}", headers=maker).json()
        assert record["submission"]["slide"]["catalogue_number"] == "LAM-0001"
        assert client.get("/api/slide-cases", headers=other).json() == []
        assert client.get(f"/api/slide-cases/{sid}", headers=other).status_code == 404
        assert client.put(f"/api/slide-cases/{sid}", json=contribution(), headers=other).status_code == 404
        assert client.delete(f"/api/slide-cases/{sid}", headers=other).status_code == 404
        assert client.get(f"/api/slide-cases/{sid}").status_code == 401

        # A change keeps the images it still names (by their token), drops the others, adds the new ones.
        before = {i["token"]: i["asset_id"] for i in record["images"]}
        changed = contribution(catalogue_number="LAM-0002")
        changed["assets"] = [changed["assets"][1], {**changed["assets"][0], "upload_id": "upload-0003"}]
        answer = client.put(f"/api/slide-cases/{sid}", json=changed, headers=maker)
        assert answer.status_code == 200, answer.text
        after = {i["token"]: i["asset_id"] for i in answer.json()["images"]}
        assert after["upload-0002"] == before["upload-0002"]  # kept, with its id
        assert "upload-0001" not in after and after["upload-0003"] not in before.values()
        assert answer.json()["submission"]["slide"]["catalogue_number"] == "LAM-0002"
        bad = client.put(f"/api/slide-cases/{sid}", json=contribution(format="custom"), headers=maker)
        assert bad.status_code == 422 and bad.json()["errors"][0]["code"] == "custom_size_missing"

        # Submitted only once every image has its file.
        refused = client.post(f"/api/slide-cases/{sid}/submit", headers=maker)
        assert refused.status_code == 409 and "need their file" in refused.json()["detail"]
        give_files(settings, sid)
        submitted = client.post(f"/api/slide-cases/{sid}/submit", headers=maker)
        assert submitted.status_code == 200 and submitted.json()["status"] == "processing"
        assert client.put(f"/api/slide-cases/{sid}", json=changed, headers=maker).status_code == 409
        assert client.delete(f"/api/slide-cases/{sid}", headers=maker).status_code == 409

        # Published once every image is processed and no job is left.
        engine = make_sync_engine(database_path(settings))
        ids = [r.id for r in sql(settings, "SELECT a.id FROM asset a JOIN slide s ON s.id = a.slide_id "
                                           "WHERE s.short_id = :s ORDER BY a.id", s=sid)]
        sql(settings, "UPDATE asset SET status = 'ready' WHERE id = :a", a=ids[0])
        assert cases.after_job(engine, "process_asset", {"asset_id": ids[0]}, False, None) is None  # one to go
        sql(settings, "UPDATE asset SET status = 'ready' WHERE id = :a", a=ids[1])
        assert cases.after_job(engine, "process_asset", {"asset_id": ids[1]}, False, None) == "published"
        assert client.get(f"/api/slides/{sid}").status_code == 200

        # Another case whose image fails goes back to draft, with the reason on the image and the case.
        second = client.post("/api/slide-cases", json=contribution(catalogue_number="LAM-0003"), headers=maker)
        sid2 = second.json()["id"]
        give_files(settings, sid2)
        assert client.post(f"/api/slide-cases/{sid2}/submit", headers=maker).json()["status"] == "processing"
        failing = sql(settings, "SELECT a.id FROM asset a JOIN slide s ON s.id = a.slide_id WHERE s.short_id = :s "
                                "ORDER BY a.id", s=sid2)[1].id
        assert cases.after_job(engine, "process_asset", {"asset_id": failing}, True,
                               "Error: the image is truncated\ndetail") == "draft"
        engine.dispose()
        back = client.get(f"/api/slide-cases/{sid2}", headers=maker).json()
        assert back["status"] == "draft" and "the image is truncated" in back["status_reason"]
        image = next(i for i in back["images"] if i["asset_id"] == failing)
        assert image["status"] == "failed" and image["failure"] == "Error: the image is truncated"

        # A draft is deleted with its uploads; a published slide is not a draft.
        assert client.delete(f"/api/slide-cases/{sid2}", headers=maker).status_code == 204
        assert client.get(f"/api/slide-cases/{sid2}", headers=maker).status_code == 404
        assert not sql(settings, "SELECT id FROM upload WHERE tus_id LIKE :t", t=f"tus-{failing}")
        assert [c["id"] for c in client.get("/api/slide-cases", headers=maker).json()] == [sid]
