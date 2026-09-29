"""Rules: what a node accepts, and whether two rules can accept the same slide.

A rule is compiled to **clauses**, alternatives each of which is a conjunction over five dimensions:

========== ============================================================================================
kinds      the anchor kind is one of these (``None``: any)
taxa       the anchor's lineage contains one of these GBIF keys, and none of ``exclude``
paths      the anchor's vocabulary path starts, segment by segment, with one of these
parts      ``specimen.part`` is one of these (``None``: any, including no part)
preservation ``specimen.preservation`` is one of these (``None``: any)
========== ============================================================================================

A taxon is accepted when it lies inside one of the clause's taxa and overlaps none of its exclusions: it may be
neither inside an excluded clade nor contain one (a class-level anchor "Insecta" is not taken by a rule "insects
other than beetles", which would claim the beetles too; it stays with the node above).

A slide is described by its **facts** (kind, key and lineage or path, part, preservation). Two clauses
**intersect** when some slide could satisfy both: every dimension must admit a common value. For taxa that means one
clause's taxon contains the other's (clades are nested or disjoint) and the deeper one is not excluded by the other
clause. The test is exact on every dimension except that a clause whose exclusions together cover a whole clade is
still counted as overlapping; that errs toward asking for a priority, never toward missing an overlap.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from app.collections.vocab import prefix_of


@dataclass(frozen=True)
class Facts:
    """What placement knows about a slide."""

    kind: str
    #: The taxon's own (accepted) GBIF key, and its lineage including itself.
    key: int | None = None
    lineage: frozenset[int] = frozenset()
    path: str | None = None
    part: str | None = None
    preservation: str = "recent"


@dataclass(frozen=True)
class Clause:
    kinds: frozenset[str] | None = None
    taxa: tuple[int, ...] = ()
    exclude: tuple[int, ...] = ()
    paths: tuple[str, ...] = ()
    parts: frozenset[str] | None = None
    preservation: frozenset[str] | None = None

    @property
    def anchored(self) -> bool:
        """Whether the clause says anything about the anchor itself."""
        return self.kinds is not None or bool(self.taxa) or bool(self.paths)

    @property
    def empty(self) -> bool:
        return not self.anchored and self.parts is None and self.preservation is None and not self.exclude

    def holds(self, f: Facts, lineages: Mapping[int, frozenset[int]]) -> bool:
        if self.kinds is not None and f.kind not in self.kinds:
            return False
        if self.taxa and (f.kind != "taxon" or not any(k in f.lineage for k in self.taxa)):
            return False
        if self.exclude and any(k in f.lineage or f.key in lineages.get(k, ()) for k in self.exclude):
            return False
        if self.paths and (f.path is None or not any(prefix_of(p, f.path) for p in self.paths)):
            return False
        if self.parts is not None and f.part not in self.parts:
            return False
        if self.preservation is not None and f.preservation not in self.preservation:
            return False
        return True


def _meet(a: frozenset[str] | None, b: frozenset[str] | None) -> frozenset[str] | None:
    if a is None:
        return b
    if b is None:
        return a
    return a & b


def conjoin(condition: Clause, clause: Clause) -> Clause:
    """A clause restricted by a condition that says nothing about taxa or paths (a container's own condition)."""
    if condition.taxa or condition.paths or condition.exclude:
        raise ValueError("a container's condition cannot name taxa or paths")
    return replace(clause, kinds=_meet(condition.kinds, clause.kinds), parts=_meet(condition.parts, clause.parts),
                   preservation=_meet(condition.preservation, clause.preservation))


def _sets_meet(a: frozenset[str] | None, b: frozenset[str] | None) -> bool:
    return a is None or b is None or bool(a & b)


def intersects(a: Clause, b: Clause, lineages: Mapping[int, frozenset[int]]) -> bool:
    """Whether some slide satisfies both clauses. ``lineages`` maps each rule taxon to its ancestors' keys."""
    if not (_sets_meet(a.kinds, b.kinds) and _sets_meet(a.parts, b.parts)
            and _sets_meet(a.preservation, b.preservation)):
        return False
    if a.paths and b.paths and not any(prefix_of(p, q) or prefix_of(q, p) for p in a.paths for q in b.paths):
        return False
    if a.taxa and b.taxa:
        return any(_clades_meet(ta, a, tb, b, lineages) for ta in a.taxa for tb in b.taxa)
    if a.taxa and b.paths or b.taxa and a.paths:
        return False
    return True


def _within(key: int, clade: int, lineages: Mapping[int, frozenset[int]]) -> bool:
    return key == clade or clade in lineages[key]


def _clades_meet(ta: int, a: Clause, tb: int, b: Clause, lineages: Mapping[int, frozenset[int]]) -> bool:
    if _within(tb, ta, lineages):
        deeper, other = tb, a
    elif _within(ta, tb, lineages):
        deeper, other = ta, b
    else:
        return False
    return not any(_within(deeper, x, lineages) for x in other.exclude)
