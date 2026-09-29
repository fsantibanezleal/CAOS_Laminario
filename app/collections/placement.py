"""Placement: where a slide belongs in the tree, and where it may be put.

The **suggestion** is found by walking down from the realms: at each level the children that accept the slide are
candidates and the one of highest priority is taken, until no child accepts. Because the tree guard refuses two
siblings that could accept the same slide with the same priority, there is never a tie, and the walk does not
depend on the order the siblings are written in (R-062).

The **accepting** nodes are every node that, with all its ancestors, accepts the slide. A contributor may place a
slide at any of them (for a pollen slide of a pine, the pollen collection is suggested and the pine's own
collection also accepts it); anywhere else needs a curator's override with a reason.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.collections.rules import Facts
from app.collections.tree import Tree, load_tree, place_facts


@dataclass(frozen=True)
class Placement:
    suggestion: str | None
    #: The node ids from the realm down to the suggestion.
    path: tuple[str, ...]
    #: Every node the slide may be placed at without an override, in tree order.
    accepting: tuple[str, ...]


def place(facts: Facts, tree: Tree | None = None) -> Placement:
    tree = tree or load_tree()
    suggestion = place_facts(tree, facts)
    path: tuple[str, ...] = ()
    if suggestion:
        node = tree.get(suggestion)
        path = tuple(n.id for n in node.ancestors + [node])
    accepting = tuple(n.id for n in tree.walk() if not n.is_view and n.accepts_path(facts, tree.lineages))
    return Placement(suggestion, path, accepting)


def accepts(node_id: str, facts: Facts, tree: Tree | None = None) -> bool:
    tree = tree or load_tree()
    node = tree.get(node_id)
    return node is not None and not node.is_view and node.accepts_path(facts, tree.lineages)
