"""R-1108: annotations are W3C Web Annotations on one asset; anyone reads them, a signed-in account adds them, and
only the author or a curator removes one."""

from __future__ import annotations

from tests.accounts.support import account, app_client, settings_for
from tests.explore.test_explore import seed

RECT = {"type": "FragmentSelector", "conformsTo": "http://www.w3.org/TR/media-frags/",
        "value": "xywh=pixel:10,20,300,40"}
POLY = {"type": "SvgSelector", "value": '<svg><polygon points="10,10 120,15 60,90"></polygon></svg>'}


def note(selector: dict, text: str = "a nit at the base of a feather", **extra) -> dict:
    return {"@context": "http://www.w3.org/ns/anno.jsonld", "type": "Annotation",
            "body": [{"type": "TextualBody", "value": text, "purpose": "commenting"}],
            "target": {"source": "https://elsewhere.example/image", "selector": selector}, **extra}


def test_annotations_are_read_by_all_added_by_accounts_and_removed_by_their_author_or_a_curator(tmp_path):
    settings = settings_for(tmp_path)
    first, second = seed(settings, [{"preparation": "smear"}, {"preparation": "section"}])
    with app_client(settings) as client:
        admin = account(client, settings, "admin", "admin@example.org")
        author = account(client, settings, "contributor", "author@example.org", issuer=admin)
        other = account(client, settings, "contributor", "other@example.org", issuer=admin)
        curator = account(client, settings, "curator", "curator@example.org", issuer=admin)

        micro = next(a for a in client.get(f"/api/slides/{first}").json()["assets"] if a["family"] == "micro")
        url = f"/api/slides/{first}/assets/{micro['id']}/annotations"
        assert client.get(url).json() == []
        assert client.post(url, json=note(RECT)).status_code == 401  # a visitor reads, and does not write

        made = client.post(url, json=note(RECT, creator={"name": "Someone else"}), headers=author)
        assert made.status_code == 201, made.text
        record = made.json()
        w3c = record["annotation"]
        assert w3c["@context"] == "http://www.w3.org/ns/anno.jsonld" and w3c["type"] == "Annotation"
        assert w3c["id"].endswith(f"/api/annotations/{record['id']}")
        # The target is the asset's own image, whatever the client sent; the creator is the account.
        media = micro["media"]
        expected_source = (media["iiif_info_url"] or "").removesuffix("/info.json") or media["image_url"] or ""
        assert w3c["target"]["source"] == expected_source and w3c["target"]["selector"] == RECT
        assert w3c["creator"]["name"] == "Test Person" and record["removable"] is True
        assert w3c["body"][0]["value"] == "a nit at the base of a feather"
        assert client.post(url, json=note(POLY), headers=other).status_code == 201

        # Only text and plain shapes are stored.
        script = {"type": "SvgSelector", "value": '<svg><script>alert(1)</script><polygon points="1,1 2,2 3,3"/></svg>'}
        for bad in (note(script), note({**RECT, "value": "xywh=pixel:10,20,0,40"}), note(RECT, text="x" * 2001),
                    note({"type": "SvgSelector", "value": '<svg><polygon points="1,1 2,2"/></svg>'})):
            assert client.post(url, json=bad, headers=author).status_code == 422

        listed = client.get(url).json()
        assert [a["removable"] for a in listed] == [False, False]  # a visitor removes nothing
        mine = client.get(url, headers=author).json()
        assert [a["removable"] for a in mine] == [True, False]
        assert [a["removable"] for a in client.get(url, headers=curator).json()] == [True, True]

        own, others = listed[0]["id"], listed[1]["id"]
        assert client.delete(f"/api/annotations/{others}", headers=author).status_code == 403
        assert client.delete(f"/api/annotations/{own}", headers=author).status_code == 204
        assert client.delete(f"/api/annotations/{others}", headers=curator).status_code == 204
        assert client.get(url).json() == []
        assert client.delete(f"/api/annotations/{own}", headers=curator).status_code == 404

        # An asset is annotated only on its own published slide.
        assert client.get(f"/api/slides/{second}/assets/{micro['id']}/annotations").status_code == 404
        assert client.get(f"/api/slides/{first}/assets/999999/annotations").status_code == 404
