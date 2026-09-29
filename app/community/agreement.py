"""The agreement rule (M8, R-088, R-1302): the community anchor of a slide from its identifications.

iNaturalist's community taxon (dossier 15, section 2; ``Observation#community_taxon_nodes`` and
``#get_community_taxon`` at commit 8bdc0a099170), on lineages of node ids so that it applies to every anchor kind.
Only the current, visible identifications count, one per account. For every node $t$ named by an identification or
on the lineage of one:

- $c(t)$, the cumulative count: identifications of $t$ or of a node below it;
- $d(t)$, the disagreement count: identifications of a node that is neither $t$'s ancestor nor below $t$;
- $a(t)$, the ancestor disagreements: identifications of an ancestor $A$ made as an explicit disagreement with the
  slide's anchor $P$ of the time, which disagree with every node from $A$'s child on $P$'s lineage down to $P$
  (counted while some current identification still names $P$ or a node below it);

and $score(t) = c / (c + d + a)$. The community node is the deepest node with $c > 1$ and $score > 2/3$ (strictly),
never a kind's root; with fewer than two identifications there is none. iNaturalist also counts an older identification
whose disagreement was never recorded as disagreeing with finer taxa; Laminario always records it, so that case does
not arise.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.community.lineage import is_root

CUTOFF = 2.0 / 3.0


@dataclass(frozen=True)
class Ident:
    """What the rule needs of an identification."""

    order: int
    account: str
    lineage: tuple[str, ...]
    current: bool = True
    hidden: bool = False
    #: True when an identification of an ancestor of ``previous`` disagrees with the finer anchor; False when it
    #: does not; None when the question did not arise (the node is not an ancestor of the slide's anchor).
    disagreement: bool | None = None
    #: The slide's anchor, as a lineage, when the identification was made.
    previous: tuple[str, ...] | None = None

    @property
    def node(self) -> str:
        return self.lineage[-1]


@dataclass(frozen=True)
class NodeScore:
    node: str
    depth: int
    cumulative: int
    disagreements: int
    ancestor_disagreements: int

    @property
    def score(self) -> float:
        total = self.cumulative + self.disagreements + self.ancestor_disagreements
        return self.cumulative / total if total else 0.0


@dataclass(frozen=True)
class Community:
    node: str | None
    lineage: tuple[str, ...] | None
    scores: list[NodeScore] = field(default_factory=list)
    #: The identifications that counted, in order.
    working: tuple[Ident, ...] = ()


def working_set(idents: list[Ident]) -> list[Ident]:
    """Current, visible identifications, one per account (the latest current one wins if the data had two)."""
    latest: dict[str, Ident] = {}
    for ident in sorted(idents, key=lambda i: i.order):
        if ident.current and not ident.hidden and ident.lineage:
            latest[ident.account] = ident
    return sorted(latest.values(), key=lambda i: i.order)


def _ancestor_disagrees(ident: Ident, prefix: tuple[str, ...], work: list[Ident]) -> bool:
    """Whether ``ident`` explicitly disagreed with a node on the branch that ``prefix`` (a node's lineage) ends in."""
    previous = ident.previous
    if not (ident.disagreement and previous):
        return False
    if ident.node not in previous[:-1]:
        return False
    # If every identification of the disagreed anchor's branch has been withdrawn, the disagreement no longer counts.
    if not any(previous[-1] in j.lineage for j in work):
        return False
    branch = set(previous[previous.index(ident.node) + 1:])
    return bool(set(prefix) & branch)


def community(idents: list[Ident]) -> Community:
    work = working_set(idents)
    if len(work) <= 1:
        return Community(None, None, [], tuple(work))
    prefixes: dict[str, tuple[str, ...]] = {}
    for ident in work:
        for depth, node in enumerate(ident.lineage):
            prefixes.setdefault(node, ident.lineage[: depth + 1])
    scores: list[NodeScore] = []
    for node, prefix in prefixes.items():
        cumulative = sum(1 for i in work if node in i.lineage)
        disagreements = sum(1 for i in work if node not in i.lineage and i.node not in prefix)
        first = next((i for i in work if node in i.lineage), None)
        ancestor = sum(1 for i in work if _ancestor_disagrees(i, prefix, work)) if first else 0
        scores.append(NodeScore(node, len(prefix) - 1, cumulative, disagreements, ancestor))
    qualifying = [s for s in scores if s.cumulative > 1 and s.score > CUTOFF and not is_root(s.node)]
    if not qualifying:
        return Community(None, None, scores, tuple(work))
    best = max(qualifying, key=lambda s: s.depth)
    return Community(best.node, prefixes[best.node], scores, tuple(work))


def categories(idents: list[Ident], result: Community) -> dict[int, str]:
    """Each working identification's category, as iNaturalist shows it (``Identification#update_observation``):
    leading (below the community anchor, or no community anchor yet), improving (the first at or above it on its
    branch), supporting (agreeing after), maverick (outside its branch)."""
    out: dict[int, str] = {}
    progressive_seen: list[Ident] = []
    lineage = result.lineage or ()
    for ident in result.working:
        if result.node is None or (result.node in ident.lineage and ident.node != result.node):
            out[ident.order] = "leading"
            continue
        on_branch = ident.node in lineage
        if not on_branch:
            out[ident.order] = "maverick"
            continue
        progressive = not any(ident.node in earlier.lineage for earlier in progressive_seen)
        out[ident.order] = "improving" if progressive else "supporting"
        progressive_seen.append(ident)
    return out
