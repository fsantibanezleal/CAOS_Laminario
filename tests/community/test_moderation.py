"""R-1305 and R-1306: flags and the curators' hiding and restoring, with the reason, recorded; a hidden slide leaves
every public listing, count, search, map, manifest and tile, and its contributor sees why."""

from __future__ import annotations

from tests.accounts.support import app_client, settings_for

from .support import POLYPLAX_ALASKENSIS, community, identify, people, published, sql


def reason(text: str = "a real record of someone else's photograph") -> dict:
    return {"reason": text}


def test_flags_and_their_resolution(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"])
        ident = identify(client, sid, p["one"], POLYPLAX_ALASKENSIS).json()["id"]

        flag = {"target_kind": "identification", "target_id": ident, "category": "wrong", "comment": "A mammal louse"}
        assert client.post("/api/flags", json=flag).status_code == 401  # a visitor does not flag
        made = client.post("/api/flags", json=flag, headers=p["maker"])
        assert made.status_code == 201, made.text
        assert made.json()["slide_id"] == sid and made.json()["by"] == "Test Person"
        assert client.post("/api/flags", json={**flag, "target_id": "nothing"},
                           headers=p["maker"]).status_code == 404
        assert client.post("/api/flags", json={**flag, "category": "boring"}, headers=p["maker"]).status_code == 422

        assert client.get("/api/flags", headers=p["one"]).status_code == 403  # an identifier does not moderate
        open_flags = client.get("/api/flags", headers=p["curator"]).json()
        assert [f["id"] for f in open_flags] == [made.json()["id"]]
        resolved = client.post(f"/api/flags/{made.json()['id']}/resolve", json={"resolution": "Checked: it stands"},
                               headers=p["curator"])
        assert resolved.status_code == 200 and resolved.json()["resolved_by"] == "Test Person"
        assert client.get("/api/flags", headers=p["curator"]).json() == []
        assert len(client.get("/api/flags?status=all", headers=p["curator"]).json()) == 1
        assert client.post(f"/api/flags/{made.json()['id']}/resolve", json={"resolution": "again"},
                           headers=p["curator"]).status_code == 409


def test_a_hidden_slide_leaves_every_public_place(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"])
        other = published(client, settings, p["maker"])
        before = {
            "list": client.get("/api/slides").json()["total"],
            "search": client.get("/api/slides?q=borealis").json()["total"],
            "facets": client.get("/api/explore/facets").json(),
            "map": client.get("/api/explore/map").json()["total"],
            "queue": client.get("/api/identify").json()["total"],
        }
        assert before["list"] == 2 and before["queue"] == 2

        assert client.post(f"/api/moderation/slide/{sid}/hide", json=reason(),
                           headers=p["one"]).status_code == 403
        assert client.post(f"/api/moderation/slide/{sid}/hide", json=reason("short"),
                           headers=p["curator"]).status_code == 422
        assert client.post(f"/api/moderation/slide/{sid}/hide", json=reason(),
                           headers=p["curator"]).status_code == 204

        # Gone from every public place.
        assert client.get(f"/api/slides/{sid}").status_code == 404
        assert client.get(f"/api/slides/{sid}/manifest").status_code == 404
        assert client.get(f"/api/slides/{sid}/identifications").status_code == 404
        assert client.get("/api/slides").json()["total"] == 1
        assert client.get("/api/slides?q=borealis").json()["total"] == 1
        assert client.get("/api/explore/map").json()["total"] == before["map"] - 1
        assert client.get("/api/identify").json()["total"] == 1
        facets = client.get("/api/explore/facets").json()
        assert facets != before["facets"]

        # Its contributor sees why, with the case.
        mine = {c["id"]: c for c in client.get("/api/slide-cases", headers=p["maker"]).json()}
        assert mine[sid]["status"] == "hidden" and "someone else's photograph" in mine[sid]["status_reason"]
        assert mine[other]["status"] == "published"

        # Only the curator who hid it, or an admin, restores it; every action is kept.
        assert client.post(f"/api/moderation/slide/{sid}/unhide", json=reason("restored after review"),
                           headers=p["curator2"]).status_code == 403
        hidden = client.get("/api/moderation/hidden", headers=p["curator2"]).json()
        assert [(h["target_kind"], h["target_id"]) for h in hidden] == [("slide", sid)]
        assert client.post(f"/api/moderation/slide/{sid}/unhide", json=reason("restored after review"),
                           headers=p["curator"]).status_code == 204
        assert client.get(f"/api/slides/{sid}").status_code == 200
        assert client.get("/api/slides").json()["total"] == 2
        actions = client.get(f"/api/moderation/actions?slide={sid}", headers=p["curator2"]).json()
        assert [a["action"] for a in actions] == ["unhide", "hide"]
        assert client.post(f"/api/moderation/slide/{sid}/hide", json=reason(),
                           headers=p["curator2"]).status_code == 204
        assert client.post(f"/api/moderation/slide/{sid}/unhide", json=reason("an admin restores it"),
                           headers=p["admin"]).status_code == 204


def test_hidden_identifications_and_annotations(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        p = people(client, settings)
        sid = published(client, settings, p["maker"])
        identify(client, sid, p["one"], POLYPLAX_ALASKENSIS)
        two = identify(client, sid, p["two"], POLYPLAX_ALASKENSIS).json()["id"]
        identify(client, sid, p["three"], POLYPLAX_ALASKENSIS)
        assert community(client, sid)["community"]["node"] == "taxon:1032575"

        # A hidden identification leaves the agreement, and only its author and the curators see it.
        assert client.post(f"/api/moderation/identification/{two}/hide", json=reason("an offensive comment here"),
                           headers=p["curator"]).status_code == 204
        seen = community(client, sid)
        assert seen["community"]["node"] == "taxon:1032563"  # two of three for the species: not above 2/3
        assert two not in [i["id"] for i in seen["identifications"]]
        assert two in [i["id"] for i in community(client, sid, p["two"])["identifications"]]
        assert two in [i["id"] for i in community(client, sid, p["curator"])["identifications"]]
        assert client.post(f"/api/identifications/{two}/restore", headers=p["two"]).status_code == 409
        assert client.post(f"/api/moderation/identification/{two}/unhide", json=reason("the comment was edited"),
                           headers=p["curator"]).status_code == 204
        assert community(client, sid)["community"]["node"] == "taxon:1032575"

        # A hidden annotation is not served to others.
        asset = sql(settings, "SELECT a.id FROM asset a JOIN slide s ON s.id = a.slide_id WHERE s.short_id = :s "
                              "AND a.family = 'micro'", s=sid)[0].id
        note = {"type": "Annotation", "body": [{"type": "TextualBody", "value": "a nymph"}],
                "target": {"selector": {"type": "FragmentSelector", "conformsTo": "http://www.w3.org/TR/media-frags/",
                                        "value": "xywh=pixel:10,10,20,20"}}}
        made = client.post(f"/api/slides/{sid}/assets/{asset}/annotations", json=note, headers=p["maker"])
        assert made.status_code == 201, made.text
        public_id = made.json()["id"].rsplit("/", 1)[-1]
        assert client.post(f"/api/moderation/annotation/{public_id}/hide", json=reason("not about the image"),
                           headers=p["curator"]).status_code == 204
        assert client.get(f"/api/slides/{sid}/assets/{asset}/annotations").json() == []
        assert len(client.get(f"/api/slides/{sid}/assets/{asset}/annotations", headers=p["maker"]).json()) == 1
