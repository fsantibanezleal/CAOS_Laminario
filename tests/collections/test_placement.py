"""Placement: real anchors land where a person would put them, and the suggestion never depends on order (R-062)."""

from __future__ import annotations

import pytest

from app.collections import vocab
from app.collections.placement import accepts, place
from app.collections.rules import Facts
from app.collections.tree import load_tree, witnesses


def taxon(*lineage: int, part: str | None = None, preservation: str = "recent") -> Facts:
    """A taxon with its backbone lineage, kingdom first, the taxon itself last (keys from tests/collections/gbif)."""
    return Facts("taxon", key=lineage[-1], lineage=frozenset(lineage), part=part, preservation=preservation)


def term(kind: str, ref: str, classification: str | None = None) -> Facts:
    return Facts(kind, path=vocab.resolve_term(kind, ref, classification).path)


POLYPLAX = (1, 54, 216, 7612838, 4369, 1032563, 1032608)
HOMO = (1, 44, 359, 798, 5483, 2436435, 2436436)
GALLUS = (1, 44, 212, 723, 9331, 2473720, 9326020)
SALMO = (1, 44, 1313, 8615, 2347608, 8215487)
PINUS = (6, 7707728, 194, 640, 3925, 2684241, 5285637)

REAL = {
    "louse": (taxon(*POLYPLAX), "life.insects.lice"),
    "human blood": (taxon(*HOMO, part="blood"), "life.mammals.blood-immune"),
    "human hair": (taxon(*HOMO, part="hair"), "life.mammals.hair"),
    "chicken feather": (taxon(*GALLUS, part="feather"), "life.birds.feathers"),
    "chicken skin": (taxon(*GALLUS, part="skin"), "life.birds.integument"),
    "trout gill": (taxon(*SALMO, part="gill"), "life.fishes.gills"),
    "trout liver": (taxon(*SALMO, part="liver"), "life.fishes.digestive"),
    "trout": (taxon(*SALMO), "life.fishes"),
    "pine pollen": (taxon(*PINUS, part="pollen"), "life.pollen.gymnosperm-pollen"),
    "pine wood": (taxon(*PINUS, part="wood"), "life.plants.gymnosperms"),
    "fossil pine pollen": (taxon(*PINUS, part="pollen", preservation="fossil"), "earth.fossils.palynomorphs"),
    "pine in amber": (taxon(*PINUS, preservation="in_amber"), "earth.fossils.amber"),
    "granite": (term("rock", "granite"), "earth.rocks.igneous.coarse"),
    "kimberlite": (term("rock", "kimberlite"), "earth.rocks.igneous.exotic"),
    "slate": (term("rock", "slate"), "earth.rocks.metamorphic.foliated"),
    "pelite": (term("rock", "pelite"), "earth.rocks.metamorphic"),
    "tufa": (term("rock", "tufa"), "earth.rocks.sedimentary.carbonate"),
    "chondrite": (term("rock", "ordinary-chondrite"), "earth.rocks.meteorites"),
    "sand": (term("rock", "sand"), "earth.rocks.soils-sediments"),
    "chromitite": (term("rock", "chromitite"), "earth.rocks.ore"),
    "quartz": (term("mineral", "Quartz"), "earth.minerals.oxides"),
    "olivine": (term("mineral", "olivine"), "earth.minerals.silicates.nesosilicates"),
    "albite": (term("mineral", "Albite"), "earth.minerals.silicates.tectosilicates"),
    "biotite": (term("mineral", "Biotite"), "earth.minerals.silicates.phyllosilicates"),
    "gold": (term("mineral", "Gold"), "earth.minerals.native-elements"),
    "weddellite": (term("mineral", "Weddellite"), "earth.minerals.organic"),
    "snow dendrite": (term("crystal", "ice/hexagonal", "P"), "matter.crystals.ice.plane"),
    "snow": (term("crystal", "ice"), "matter.crystals.ice"),
    "salt crystals": (term("crystal", "chemical/cubic"), "matter.crystals.chemical"),
    "cotton": (term("material", "cotton"), "matter.materials.fibres"),
    "honey": (term("material", "honey-sample"), "life.pollen.airborne-honey"),
    "animal of unknown phylum": (taxon(1), "life"),
}


@pytest.mark.parametrize("name", list(REAL))
def test_real_anchors(name):
    facts, expected = REAL[name]
    assert place(facts).suggestion == expected


# R-062
def test_deterministic_suggestion():
    tree = load_tree()
    backwards = tree.reversed_copy()
    assert [n.id for n in backwards.roots] == ["matter", "earth", "life"]
    cases = [facts for facts, _ in REAL.values()]
    cases += [f for node in tree.walk() if not node.is_view for f in witnesses(node, tree)]
    assert len(cases) > 400
    for facts in cases:
        first = place(facts, tree)
        assert place(facts, tree) == first
        again = place(facts, backwards)
        assert again.suggestion == first.suggestion and again.path == first.path
        assert set(again.accepting) == set(first.accepting)


def test_accepting_nodes_are_the_suggestion_its_path_and_the_alternatives():
    placed = place(taxon(*PINUS, part="pollen"))
    assert placed.path == ("life", "life.pollen", "life.pollen.gymnosperm-pollen")
    assert set(placed.accepting) == {"life", "life.pollen", "life.pollen.gymnosperm-pollen", "life.plants",
                                     "life.plants.gymnosperms"}
    assert accepts("life.plants.gymnosperms", taxon(*PINUS, part="pollen"))
    assert not accepts("life.plants.monocots", taxon(*PINUS, part="pollen"))
    assert not accepts("life.mammals.parasites-hosts", taxon(*HOMO)), "a view takes no slides"
    assert not accepts("life.nowhere", taxon(*HOMO))
