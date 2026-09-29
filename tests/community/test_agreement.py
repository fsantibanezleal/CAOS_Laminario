"""R-088 and R-1302: the agreement rule on the scenario table of dossier 15, section 6, and the categories.

S1 and S2 are species of genus G in family F (backbone keys made up for the table); each scenario lists the
accounts' identifications in the order they were made.
"""

from __future__ import annotations

import pytest

from app.collections.taxa import Lineage
from app.collections.vocab import Term
from app.community.agreement import Ident, categories, community
from app.community.lineage import taxon_lineage, term_lineage

ANCESTORS = (1, 54, 216, 1470)  # kingdom to order


def taxon(key: int, *above: int) -> tuple[str, ...]:
    return taxon_lineage(Lineage(key, str(key), "species", "accepted", None, (*ANCESTORS, *above)))


F = taxon(7000)
G = taxon(1000, 7000)
S1 = taxon(1001, 7000, 1000)
S2 = taxon(1002, 7000, 1000)
GRANITE = term_lineage("rock", Term("granite", None, "igneous.coarse"))
GRANODIORITE = term_lineage("rock", Term("granodiorite", None, "igneous.coarse"))
QUARTZ = term_lineage("mineral", Term("Quartz", "species", "4.D.A.05", "4.DA.05"))
QUARTZITE = term_lineage("rock", Term("quartzite", None, "metamorphic.foliated"))


def idents(*items) -> list[Ident]:
    """Items are (account, lineage) or (account, lineage, extra) with extra the Ident keywords."""
    out = []
    for order, item in enumerate(items):
        account, lineage, *rest = item
        out.append(Ident(order=order, account=account, lineage=lineage, **(rest[0] if rest else {})))
    return out


SCENARIOS = [
    (1, idents(("a", S1)), None),
    (2, idents(("a", S1), ("b", S1)), S1),
    (3, idents(("a", S1), ("b", S2)), G),
    (4, idents(("a", S1), ("b", S1), ("c", S1), ("d", S2)), S1),
    (5, idents(("a", S1), ("b", S1), ("c", S2)), G),
    (6, idents(("a", S1), ("b", S1), ("c", G, {"disagreement": True, "previous": S1})), G),
    (7, idents(("a", S1), ("b", S1), ("c", G, {"disagreement": False, "previous": S1})), S1),
    (8, idents(("a", S1), ("b", S1), ("c", S2, {"current": False})), S1),
    (9, idents(("a", S1), ("b", S1), ("c", S2, {"hidden": True})), S1),
    (10, idents(("a", GRANITE), ("b", GRANODIORITE)), ("rock", "rock:igneous", "rock:igneous.coarse")),
    (11, idents(("a", QUARTZ), ("b", QUARTZITE)), None),
    (12, idents(("a", S1), ("b", S1), ("a", S2)), G),
]


@pytest.mark.parametrize(("number", "given", "expected"), SCENARIOS, ids=[f"scenario-{s[0]}" for s in SCENARIOS])
def test_scenario_table(number, given, expected):
    result = community(given)
    assert result.lineage == expected, f"scenario {number}: {result.node}"
    if expected is not None:
        assert result.node == expected[-1]


def test_scores_are_the_formula():
    """Scenario 6 in numbers: S1 scores 2 / (2 + 0 + 1), not more than two thirds; G scores 3 / 3."""
    result = community(idents(("a", S1), ("b", S1), ("c", G, {"disagreement": True, "previous": S1})))
    by_node = {s.node: s for s in result.scores}
    s1, g = by_node[S1[-1]], by_node[G[-1]]
    assert (s1.cumulative, s1.disagreements, s1.ancestor_disagreements) == (2, 0, 1)
    assert s1.score == pytest.approx(2 / 3)
    assert (g.cumulative, g.disagreements, g.ancestor_disagreements, g.score) == (3, 0, 0, 1.0)
    # Scenario 4: three for S1 against one for S2.
    four = {s.node: s for s in community(idents(("a", S1), ("b", S1), ("c", S1), ("d", S2))).scores}
    assert four[S1[-1]].score == pytest.approx(0.75)


def test_a_withdrawn_disagreement_stops_counting():
    """An explicit disagreement with S1 no longer counts once nobody names S1 or below (iNaturalist's rule)."""
    given = idents(("a", S1, {"current": False}), ("b", G, {"disagreement": True, "previous": S1}),
                   ("c", G))
    by_node = {s.node: s for s in community(given).scores}
    assert by_node[G[-1]].ancestor_disagreements == 0


def test_categories():
    given = idents(("a", S1), ("b", S1), ("c", S1, {"current": True}), ("d", S2))
    result = community(given)
    assert result.node == S1[-1]
    assert categories(given, result) == {0: "improving", 1: "supporting", 2: "supporting", 3: "maverick"}
    finer = idents(("a", G), ("b", G), ("c", S1))
    result = community(finer)
    assert result.node == G[-1]
    assert categories(finer, result) == {0: "improving", 1: "supporting", 2: "leading"}
