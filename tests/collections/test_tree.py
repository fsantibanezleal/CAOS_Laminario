"""The tree guard: integrity (R-060) and sibling overlaps (R-061), on the real tree and on broken copies of it."""

from __future__ import annotations

import copy

from app.collections.rules import Facts
from app.collections.tree import _raw, build_tree, check_tree, counts, load_tree, sibling_overlaps
from app.services.collections import facet_icons
from tests.collections.support import sprite_symbols


def _find(raw: dict, path: str) -> dict:
    nodes = raw["nodes"]
    node = None
    for segment in path.split("."):
        node = next(n for n in nodes if n["id"] == segment)
        nodes = node.get("children") or []
    return node


# R-060
def test_tree_integrity():
    tree = load_tree()
    symbols = sprite_symbols()
    assert check_tree(tree, icons=symbols) == []
    assert counts(tree) == {"realm": 3, "collection": 18, "sub-collection and group": 130}
    node_icons = {n.icon for n in tree.walk()}
    assert symbols == node_icons | facet_icons(), "every icon belongs to a node or a facet, and each has one"
    assert len(symbols) == 186
    for node in tree.walk():
        assert node.rule.clauses, node.id
        assert node.name["en"] and node.name["es"] and node.about["en"] and node.about["es"], node.id


def test_the_guard_finds_defects():
    raw = copy.deepcopy(_raw())
    birds = _find(raw, "life.birds")
    birds["name"]["es"] = ""
    birds["children"].append({"id": "Bad_Id", "level": "sub-collection", "name": {"en": "x", "es": "x"},
                              "about": {"en": "x" * 30, "es": "x" * 30}, "rule": {"parts": ["wing-of-bat"]}})
    _find(raw, "earth.rocks.igneous.coarse")["rule"] = {"paths": ["igneous.plutonic"]}
    defects = check_tree(build_tree(raw), icons=sprite_symbols())
    text = "\n".join(defects)
    assert "life.birds: no es name" in text
    assert "life.birds.Bad_Id: id segment" in text
    assert "unknown part wing-of-bat" in text
    assert "path igneous.plutonic matches nothing" in text
    assert "icon life.birds.Bad_Id is not in the sprite" in text


# R-061
def test_sibling_overlap_needs_priority():
    tree = load_tree()
    for siblings in [tree.roots] + [n.children for n in tree.walk()]:
        assert sibling_overlaps(siblings, tree) == []

    raw = copy.deepcopy(_raw())
    del _find(raw, "life.fungi.lichens")["rule"]["priority"]
    broken = build_tree(raw)
    assert sibling_overlaps(broken.get("life.fungi").children, broken) == [
        "life.fungi.sac-fungi and life.fungi.lichens overlap with the same priority 0"
    ]
    assert any("overlap" in d for d in check_tree(broken))

    raw = copy.deepcopy(_raw())
    del _find(raw, "life.insects.other-orders")["rule"]["exclude"]
    broken = build_tree(raw)
    overlaps = sibling_overlaps(broken.get("life.insects").children, broken)
    assert "life.insects.lice and life.insects.other-orders overlap with the same priority 0" in overlaps
    assert len(overlaps) == 7

    raw = copy.deepcopy(_raw())
    _find(raw, "life.pollen")["rule"] = {}
    broken = build_tree(raw)
    assert "life.plants and life.pollen overlap with the same priority 0" in sibling_overlaps(broken.roots[0].children,
                                                                                               broken)


def test_an_anchor_that_contains_an_excluded_clade_stays_above():
    tree = load_tree()
    insecta = Facts("taxon", key=216, lineage=frozenset({1, 54, 216}))
    assert [n.id for n in tree.get("life.insects").children if n.accepts(insecta, tree.lineages)] == []
    barklouse = Facts("taxon", key=-1, lineage=frozenset({1, 54, 216, 7612838, -1}))
    assert tree.get("life.insects.other-orders").accepts(barklouse, tree.lineages)
    chordata = Facts("taxon", key=44, lineage=frozenset({1, 44}))
    assert not tree.get("life.fishes").accepts(chordata, tree.lineages)


def test_the_lock_names_every_taxon_with_a_lineage():
    tree = load_tree()
    assert len(tree.taxa) == 134
    by_name = {spec.split("@")[0]: v for spec, v in tree.taxa.items()}
    assert by_name["Pediculidae"]["lineage"] == [1, 54, 216, 7612838]
    assert by_name["Aves"] == {"key": 212, "name": "Aves", "rank": "class", "status": "accepted", "lineage": [1, 44]}
    for spec, entry in tree.taxa.items():
        assert spec.split("@")[1] == entry["rank"], spec
        assert entry["status"] in ("accepted", "doubtful"), spec
