"""The collection tree over HTTP: browsing, anchors, placement, submissions checked against the tree, IIIF."""

from __future__ import annotations

import copy

import jsonschema
import pytest

from tests import payloads
from tests.accounts.support import account, app_client, settings_for
from tests.delivery.support import iiif_schema, seed_slide


@pytest.fixture(scope="module")
def validator(tmp_path_factory):
    schema = iiif_schema(tmp_path_factory.mktemp("iiif-schema"))
    return jsonschema.Draft7Validator(schema, format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER)


def case(**changes) -> dict:
    payload = copy.deepcopy(payloads.contribution())
    for path, value in changes.items():
        target = payload
        *parents, last = path.split("__")
        for key in parents:
            target = target[key]
        target[last] = value
    return payload


def test_the_tree_the_nodes_and_the_facets(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        tree = client.get("/api/collections").json()
        assert [r["id"] for r in tree["realms"]] == ["life", "earth", "matter"]
        assert tree["counts"] == {"realm": 3, "collection": 18, "sub-collection and group": 130}
        birds = next(c for c in tree["realms"][0]["children"] if c["id"] == "life.birds")
        assert birds["name"] == {"en": "Birds", "es": "Aves"} and birds["icon"] == "life.birds"
        assert birds["defined_by"][0] == {"kind": "taxon", "value": "212", "label": "Aves (class)",
                                          "url": "https://www.gbif.org/species/212"}
        view = next(c for c in birds["children"] if c["id"] == "life.birds.parasites-hosts")
        assert view["view"] is True and view["icon"] == "organ.parasites-hosts"

        node = client.get("/api/collections/earth.minerals.silicates.tectosilicates").json()
        assert [p["id"] for p in node["path"]] == ["earth", "earth.minerals", "earth.minerals.silicates",
                                                   "earth.minerals.silicates.tectosilicates"]
        assert [d["label"] for d in node["node"]["defined_by"]] == ["Nickel-Strunz 9.F", "Nickel-Strunz 9.G"]
        assert node["iiif_collection_url"].endswith("/api/collections/earth.minerals.silicates.tectosilicates/iiif")
        assert client.get("/api/collections/life.dragons").status_code == 404

        facets = {f["id"]: f for f in client.get("/api/facets").json()}
        assert {k: len(f["values"]) for k, f in facets.items()} == {"preparation": 10, "modality": 9,
                                                                    "plant-organ": 9, "crystal-system": 7}
        assert facets["modality"]["values"][5] == {"id": "polarised_xpl", "icon": "facet.modality.polarised_xpl",
                                                   "name": {"en": "Crossed polars", "es": "Nícoles cruzados"}}


def test_anchor_search_and_placement(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        olivine = client.get("/api/anchors/search", params={"kind": "mineral", "q": "olivi"}).json()
        assert olivine[0] == {"ref": "Olivine", "name": "Olivine", "rank": "group", "classification": "9.AC.05",
                              "context": None}
        lice = client.get("/api/anchors/search", params={"kind": "taxon", "q": "Polyplax"}).json()
        assert lice[0]["ref"] == "1032563" and "Psocodea" in lice[0]["context"]
        assert client.get("/api/anchors/search", params={"kind": "taxon", "q": "P"}).status_code == 422

        placed = client.post("/api/placement", json={"anchor": {"kind": "taxon", "ref": "1032608",
                                                                "name": "Polyplax borealis"}}).json()
        assert placed["suggestion"] == "life.insects.lice"
        assert [p["id"] for p in placed["path"]] == ["life", "life.insects", "life.insects.lice"]
        assert placed["anchor"]["rank"] == "species"

        quartz = client.post("/api/placement", json={"anchor": {"kind": "mineral", "ref": "quartz",
                                                               "name": "quartz"}}).json()
        assert quartz["suggestion"] == "earth.minerals.oxides"
        assert quartz["anchor"]["ref"] == "Quartz" and quartz["anchor"]["classification"] == "4.DA.05"

        pollen = client.post("/api/placement", json={"anchor": {"kind": "taxon", "ref": "5285637",
                                                               "name": "Pinus sylvestris"}, "part": "pollen"}).json()
        assert pollen["suggestion"] == "life.pollen.gymnosperm-pollen"
        assert "life.plants.gymnosperms" in pollen["accepting"]

        unknown = client.post("/api/placement", json={"anchor": {"kind": "mineral", "ref": "kryptonite",
                                                                "name": "kryptonite"}}).json()
        assert unknown["suggestion"] is None and unknown["errors"][0]["field"] == "anchor.ref"
        bad_part = client.post("/api/placement", json={"anchor": {"kind": "taxon", "ref": "1032608", "name": "x"},
                                                       "part": "wing-of-bat"}).json()
        assert bad_part["errors"][0]["field"] == "specimen.part"


def test_submissions_are_checked_against_the_tree(tmp_path):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        admin = account(client, settings, "admin", "admin@example.org")
        contributor = account(client, settings, "contributor", "c@example.org", issuer=admin)
        curator = account(client, settings, "curator", "k@example.org", issuer=admin)

        assert client.post("/api/slide-cases", json=case(), headers=contributor).status_code == 201

        wrong = client.post("/api/slide-cases", json=case(placement__node="earth.minerals"), headers=contributor)
        assert wrong.status_code == 422
        error = wrong.json()["errors"][0]
        assert error["field"] == "placement.node" and error["expected"].startswith("life.insects.lice (suggested)")

        view = client.post("/api/slide-cases", json=case(placement__node="life.mammals.parasites-hosts"),
                           headers=contributor)
        assert view.status_code == 422 and "view" in view.json()["errors"][0]["message"]
        nowhere = client.post("/api/slide-cases", json=case(placement__node="life.dragons"), headers=contributor)
        assert nowhere.status_code == 422

        not_backbone = case()
        not_backbone["specimen"]["anchor"]["ref"] = "298129616"
        refused = client.post("/api/slide-cases", json=not_backbone, headers=contributor)
        assert refused.json()["errors"][0]["field"] == "specimen.anchor.ref"

        override = case(placement__node="earth.minerals", placement__override_reason="a louse mounted on a mineral")
        assert client.post("/api/slide-cases", json=override, headers=contributor).status_code == 403
        assert client.post("/api/slide-cases", json=override, headers=curator).status_code == 201

        mineral = case(placement__node="earth.minerals.oxides")
        mineral["specimen"]["anchor"] = {"kind": "mineral", "ref": "quartz", "name": "Rock crystal"}
        del mineral["specimen"]["host"]
        assert client.post("/api/slide-cases", json=mineral, headers=contributor).status_code == 201
        no_class = copy.deepcopy(mineral)
        no_class["specimen"]["anchor"] = {"kind": "mineral", "ref": "Abellaite", "name": "abellaite"}
        no_class["placement"]["node"] = "earth.minerals.carbonates"
        assert client.post("/api/slide-cases", json=no_class,
                           headers=contributor).json()["errors"][0]["field"] == "specimen.anchor.classification"
        no_class["specimen"]["anchor"]["classification"] = "5"
        assert client.post("/api/slide-cases", json=no_class, headers=contributor).status_code == 201

        fossil_mineral = copy.deepcopy(mineral)
        fossil_mineral["specimen"]["preservation"] = "fossil"
        assert client.post("/api/slide-cases/validate", json=fossil_mineral).json()["errors"][0]["field"] == \
            "specimen.preservation"


def test_host_views_and_iiif_collections(tmp_path, validator):
    settings = settings_for(tmp_path)
    with app_client(settings) as client:
        assert client.post("/api/slide-cases/validate", json=case()).status_code == 200  # caches louse and host
    slide_id = seed_slide(settings, [{"family": "micro", "media_kind": "image", "licence_uri":
                                      "https://creativecommons.org/licenses/by/4.0/", "creator": "A. Contributor",
                                      "width_px": 800, "height_px": 600, "modality": "brightfield",
                                      "storage_key": "x.jpg"}])
    with app_client(settings) as client:
        view = client.get("/api/slides", params={"node": "life.mammals.parasites-hosts"}).json()
        assert [s["id"] for s in view["items"]] == [slide_id]
        assert client.get("/api/slides", params={"node": "life.birds.parasites-hosts"}).json()["total"] == 0
        tree = client.get("/api/collections").json()
        mammals = next(c for c in tree["realms"][0]["children"] if c["id"] == "life.mammals")
        assert next(c for c in mammals["children"] if c["view"])["slide_count"] == 1
        insects = next(c for c in tree["realms"][0]["children"] if c["id"] == "life.insects")
        assert insects["slide_count"] == 1 and tree["realms"][0]["slide_count"] == 1

        for node in ("life.insects.lice", "life.insects", "life", "life.mammals.parasites-hosts"):
            response = client.get(f"/api/collections/{node}/iiif")
            assert response.status_code == 200 and response.headers["access-control-allow-origin"] == "*"
            document = response.json()
            errors = sorted(validator.iter_errors(document), key=str)
            assert not errors, (node, [e.message for e in errors[:3]])
            assert document["type"] == "Collection" and document["label"]["es"]
        lice = client.get("/api/collections/life.insects.lice/iiif").json()
        assert lice["items"][-1]["id"].endswith(f"/api/slides/{slide_id}/manifest")
        assert lice["partOf"][0]["id"].endswith("/api/collections/life.insects/iiif")
        insects_doc = client.get("/api/collections/life.insects/iiif").json()
        assert [i["type"] for i in insects_doc["items"]] == ["Collection"] * 8
        manifest = client.get(f"/api/slides/{slide_id}/manifest").json()
        assert manifest["partOf"][0]["id"] == lice["id"], "the manifest's partOf is served"
