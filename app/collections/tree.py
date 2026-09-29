"""The collection tree: nodes of ``data/tree.yaml`` with their rules compiled against the taxa lock.

``load_tree()`` reads the file once, expands the shared vertebrate organ systems into each vertebrate collection,
turns every ``Name@rank`` into its locked GBIF key and every rule into clauses (``app.collections.rules``).

``check_tree()`` is the tree guard: it returns every defect it finds, and the tests require none (R-060, R-061).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.collections import vocab
from app.collections.rules import Clause, Facts, conjoin, intersects

DATA = Path(__file__).resolve().parent / "data"
LEVELS = ("realm", "collection", "sub-collection", "group")
SEGMENT = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RULE_FIELDS = {"taxa", "exclude", "kind", "paths", "parts", "preservation", "any", "priority", "relation"}
KINDS = {"taxon", "rock", "mineral", "crystal", "material"}
PRESERVATION = {"recent", "fossil", "in_amber"}


@dataclass(frozen=True)
class Rule:
    clauses: tuple[Clause, ...]
    priority: int = 0
    relation: str | None = None
    #: The rule as written, for display and for the guard.
    source: dict = field(default_factory=dict, compare=False, hash=False)

    @property
    def anchored(self) -> bool:
        return any(c.anchored for c in self.clauses)


@dataclass(eq=False)
class Node:
    id: str
    segment: str
    level: str
    name: dict[str, str]
    about: dict[str, str]
    icon: str
    rule: Rule
    parent: Node | None = None
    children: list[Node] = field(default_factory=list)
    #: The shared set the node comes from (the vertebrate organ systems), if any.
    shared: str | None = None

    @property
    def is_view(self) -> bool:
        return self.rule.relation is not None

    @property
    def is_container(self) -> bool:
        return bool(self.children) and not self.rule.anchored

    @property
    def ancestors(self) -> list[Node]:
        out, node = [], self.parent
        while node is not None:
            out.append(node)
            node = node.parent
        return out[::-1]

    def own(self, f: Facts, lineages: Mapping[int, frozenset[int]]) -> bool:
        return any(c.holds(f, lineages) for c in self.rule.clauses)

    def accepts(self, f: Facts, lineages: Mapping[int, frozenset[int]]) -> bool:
        """Whether this node takes the slide, given that its parent does."""
        if self.is_view or not self.own(f, lineages):
            return False
        if self.is_container:
            return any(child.accepts(f, lineages) for child in self.children)
        return True

    def accepts_path(self, f: Facts, lineages: Mapping[int, frozenset[int]]) -> bool:
        """Whether the node and every ancestor take the slide: the nodes a contributor may choose."""
        return all(n.accepts(f, lineages) for n in self.ancestors + [self])

    def effective(self) -> list[Clause]:
        """The clauses of everything this node accepts, for comparing it with its siblings."""
        if not self.is_container:
            return list(self.rule.clauses)
        out = []
        for condition in self.rule.clauses:
            for child in self.children:
                if not child.is_view:
                    out += [conjoin(condition, c) for c in child.effective()]
        return out


@dataclass
class Tree:
    roots: list[Node]
    nodes: dict[str, Node]
    #: GBIF key and lineage of every taxon the tree names, from the lock.
    taxa: dict[str, dict]
    lineages: dict[int, frozenset[int]]

    def get(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def walk(self) -> Iterator[Node]:
        stack = list(reversed(self.roots))
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def reversed_copy(self) -> Tree:
        """The same tree with every list of siblings in reverse order (a determinism check: order must not matter)."""
        return build_tree(_raw(), reverse=True)


class TreeError(ValueError):
    pass


def _raw() -> dict:
    return yaml.safe_load((DATA / "tree.yaml").read_text(encoding="utf-8"))


def _lock() -> dict:
    return json.loads((DATA / "taxa.lock.json").read_text(encoding="utf-8"))["taxa"]


def compile_rule(raw: dict | None, taxa: dict[str, dict]) -> Rule:
    """Compile a rule as written into clauses; an unknown field or an unlocked taxon is an error."""
    raw = raw or {}
    unknown = set(raw) - RULE_FIELDS
    if unknown:
        raise TreeError(f"unknown rule fields {sorted(unknown)}")

    def flat(specs: list | None) -> list[str]:
        """Names, with lists reused through YAML aliases (the lice families) spliced in."""
        return [s for item in specs or [] for s in (flat(item) if isinstance(item, list) else [item])]

    def keys(specs: list | None) -> tuple[int, ...]:
        out = []
        for spec in flat(specs):
            if spec not in taxa:
                raise TreeError(f"{spec} is not in the taxa lock (run scripts/lock_taxa.py)")
            out.append(taxa[spec]["key"])
        return tuple(out)

    def clause(r: dict) -> Clause:
        kinds = {r["kind"]} if r.get("kind") else None
        if r.get("taxa"):
            kinds = (kinds or {"taxon"}) & {"taxon"}
        return Clause(
            kinds=frozenset(kinds) if kinds is not None else None,
            taxa=keys(r.get("taxa")),
            exclude=keys(r.get("exclude")),
            paths=tuple(str(p) for p in r.get("paths") or ()),
            parts=frozenset(r["parts"]) if r.get("parts") else None,
            preservation=frozenset(r["preservation"]) if r.get("preservation") else None,
        )

    base = {k: v for k, v in raw.items() if k not in ("any", "priority", "relation")}
    alternatives = raw.get("any")
    clauses = tuple(clause({**base, **alt}) for alt in alternatives) if alternatives else (clause(base),)
    return Rule(clauses=clauses, priority=int(raw.get("priority", 0)), relation=raw.get("relation"), source=raw)


def build_tree(raw: dict, *, reverse: bool = False) -> Tree:
    lock = _lock()
    nodes: dict[str, Node] = {}
    shared = raw.get("shared") or {}

    def make(spec: dict, parent: Node | None, shared_from: str | None = None) -> Node:
        segment = spec["id"]
        node_id = f"{parent.id}.{segment}" if parent else segment
        node = Node(id=node_id, segment=segment, level=spec.get("level", ""), name=spec.get("name") or {},
                    about=spec.get("about") or {}, icon=spec.get("icon") or node_id,
                    rule=compile_rule(spec.get("rule"), lock), parent=parent, shared=shared_from)
        if node_id in nodes:
            raise TreeError(f"duplicate node id {node_id}")
        nodes[node_id] = node
        children = []
        if spec.get("shared"):
            if spec["shared"] not in shared:
                raise TreeError(f"{node_id}: unknown shared set {spec['shared']}")
            children += [make(s, node, spec["shared"]) for s in shared[spec["shared"]]]
        children += [make(c, node) for c in spec.get("children") or []]
        node.children = children[::-1] if reverse else children
        return node

    roots = [make(r, None) for r in raw["nodes"]]
    lineages = {v["key"]: frozenset(v["lineage"]) for v in lock.values()}
    return Tree(roots=roots[::-1] if reverse else roots, nodes=nodes, taxa=lock, lineages=lineages)


@lru_cache(maxsize=1)
def load_tree() -> Tree:
    return build_tree(_raw())


# --- the guard ------------------------------------------------------------------------------------------------

def counts(tree: Tree) -> dict[str, int]:
    """Realms, collections, and sub-collections and groups with each shared set counted once (as its icons are)."""
    seen_shared: set[str] = set()
    out = {"realm": 0, "collection": 0, "sub-collection and group": 0}
    for node in tree.walk():
        if node.level in ("realm", "collection"):
            out[node.level] += 1
        elif node.shared:
            if node.icon not in seen_shared:
                seen_shared.add(node.icon)
                out["sub-collection and group"] += 1
        else:
            out["sub-collection and group"] += 1
    return out


def witnesses(node: Node, tree: Tree) -> list[Facts]:
    """Slides the node should take: along its path, each dimension takes a value its rule allows.

    Several are tried (every part, preservation and path the node itself names, the first taxa), because a
    higher-priority sibling may rightly take some of them. For a container the witnesses come from its children.
    A taxon witness is a hypothetical species inside the rule's clade (key: the clade's key negated), so it lies
    outside every excluded sub-clade, as the species such a rule is written for do.
    """
    if node.is_container:
        return [f for c in node.children if not c.is_view for f in witnesses(c, tree)]
    chain = node.ancestors + [node]
    kind, key, lineage, path, part, preservation = None, None, frozenset(), None, None, "recent"
    for n in chain[:-1]:
        c = n.rule.clauses[0]
        kind = sorted(c.kinds)[0] if c.kinds else kind
        if c.taxa:
            key, lineage, kind = -c.taxa[0], tree.lineages[c.taxa[0]] | {c.taxa[0], -c.taxa[0]}, "taxon"
        path = c.paths[0] if c.paths else path
        part = sorted(c.parts)[0] if c.parts else part
        preservation = sorted(c.preservation)[0] if c.preservation else preservation
    out = []
    for c in node.rule.clauses:
        kinds = sorted(c.kinds) if c.kinds else [kind]
        taxa = [(-k, tree.lineages[k] | {k, -k}) for k in c.taxa[:3]] or [(key, lineage)]
        for k, (tk, lin), p, pa, pr in (
            (k, t, p, pa, pr)
            for k in kinds for t in taxa
            for p in (c.paths or (path,)) for pa in (sorted(c.parts) if c.parts else [part])
            for pr in (sorted(c.preservation) if c.preservation else [preservation])
        ):
            k = "taxon" if c.taxa else (k or ("taxon" if lin else "rock"))
            out.append(Facts(kind=k, key=tk, lineage=lin, path=p, part=pa, preservation=pr))
    return out


def check_tree(tree: Tree, icons: set[str] | None = None) -> list[str]:
    """Every defect of the tree: integrity (R-060) and sibling overlaps without a priority (R-061)."""
    v = vocab.load()
    known_paths = {"rock": v.rock_paths(), "mineral": v.mineral_paths(), "crystal": v.crystal_paths(),
                   "material": v.material_paths()}
    all_paths = set().union(*known_paths.values())
    defects: list[str] = []
    for node in tree.walk():
        depth = len(node.ancestors)
        where = node.id
        if not SEGMENT.match(node.segment):
            defects.append(f"{where}: id segment is not lower-case words joined by hyphens")
        if node.level not in LEVELS:
            defects.append(f"{where}: level {node.level!r} is not one of {LEVELS}")
        elif LEVELS.index(node.level) != depth:
            defects.append(f"{where}: level {node.level} at depth {depth}")
        for lang in ("en", "es"):
            if not (node.name.get(lang) or "").strip():
                defects.append(f"{where}: no {lang} name")
            if len((node.about.get(lang) or "").strip()) < 20:
                defects.append(f"{where}: no {lang} description")
        if icons is not None and node.icon not in icons:
            defects.append(f"{where}: icon {node.icon} is not in the sprite")
        rule = node.rule
        if rule.relation not in (None, "host"):
            defects.append(f"{where}: unknown relation {rule.relation}")
        if rule.relation and not (node.parent and node.parent.rule.anchored):
            defects.append(f"{where}: a host view needs a parent with taxa")
        if not node.is_view and all(c.empty for c in rule.clauses) and not node.children:
            defects.append(f"{where}: a leaf without a rule")
        for c in rule.clauses:
            if c.kinds and not c.kinds <= KINDS:
                defects.append(f"{where}: unknown kind {sorted(c.kinds - KINDS)}")
            if c.preservation and not c.preservation <= PRESERVATION:
                defects.append(f"{where}: unknown preservation {sorted(c.preservation - PRESERVATION)}")
            for part in c.parts or ():
                if part not in v.parts:
                    defects.append(f"{where}: unknown part {part}")
            context = c.kinds or next((cl.kinds for a in reversed(node.ancestors) for cl in a.rule.clauses
                                       if cl.kinds), None)
            scope = set().union(*(known_paths.get(k, set()) for k in context)) if context else all_paths
            for p in c.paths:
                if p not in scope:
                    defects.append(f"{where}: path {p} matches nothing in the vocabulary")
        if node.is_container and any(c.taxa or c.paths for c in rule.clauses):
            defects.append(f"{where}: a container cannot name taxa or paths")
        if not node.is_view:
            tried = witnesses(node, tree)
            placed = []
            for f in tried:
                try:
                    placed.append(place_facts(tree, f))
                except TreeError as exc:
                    defects.append(f"{where}: a tie on the way down, {exc}")
            if not any(p == node.id or (p or "").startswith(node.id + ".") for p in placed):
                defects.append(f"{where}: unreachable, its witnesses are placed at {sorted(set(map(str, placed)))}")
    for siblings in [tree.roots] + [n.children for n in tree.walk()]:
        defects += sibling_overlaps(siblings, tree)
    return defects


def sibling_overlaps(siblings: list[Node], tree: Tree) -> list[str]:
    """Pairs of siblings that can accept the same slide with the same priority (R-061)."""
    out = []
    places = [n for n in siblings if not n.is_view]
    for i, a in enumerate(places):
        for b in places[i + 1:]:
            if a.rule.priority != b.rule.priority:
                continue
            if any(intersects(x, y, tree.lineages) for x in a.effective() for y in b.effective()):
                out.append(f"{a.id} and {b.id} overlap with the same priority {a.rule.priority}")
    return out


def place_facts(tree: Tree, f: Facts) -> str | None:
    """The deepest node reached by always following the accepting child of highest priority."""
    level, found = tree.roots, None
    while True:
        candidates = [n for n in level if n.accepts(f, tree.lineages)]
        if not candidates:
            return found.id if found else None
        top = max(n.rule.priority for n in candidates)
        best = [n for n in candidates if n.rule.priority == top]
        if len(best) > 1:
            raise TreeError(f"{' and '.join(n.id for n in best)} both take {f} with priority {top}")
        found = best[0]
        level = found.children
