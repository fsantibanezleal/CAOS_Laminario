"""Every anchor as a lineage: the node ids from its kind's root down to the anchor itself (dossier 15, section 5).

The agreement rule compares identifications of any kind by their lineages, so it needs one hierarchy per kind:

- taxon: the GBIF backbone keys from the kingdom down, then the (accepted) taxon:
  ``taxon``, ``taxon:1``, ..., ``taxon:1032608``;
- mineral: the Nickel-Strunz path, then the species (a group stops at its code):
  ``mineral:9``, ``mineral:9.A``, ..., ``mineral:9.A.C.05/forsterite``;
- rock: the family path, then the rock: ``rock:igneous``, ``rock:igneous.coarse``, ``rock:igneous.coarse/granite``;
- crystal: the origin, then the snow category, then the system: ``crystal:ice``, ``crystal:ice.P``,
  ``crystal:ice.P/hexagonal``;
- material: the family, then the material: ``material:fibre``, ``material:fibre/cotton``.

Every kind has its own root, so identifications of two kinds share only nothing: a rock against a mineral is a
disagreement. A lineage is stored with the identification as it was when it was made.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.collections import vocab
from app.collections.taxa import Lineage

ROOTS = ("taxon", "mineral", "rock", "crystal", "material")

#: Ranks at species or below, where a taxon is identified as far as the collection needs.
SPECIES_OR_BELOW = {"species", "subspecies", "variety", "form", "subvariety", "subform", "infraspecific_name"}
#: Ranks above family, which even a vote of "as good as it can be" leaves too coarse.
FAMILY_OR_ABOVE = {"kingdom", "phylum", "class", "order", "family", "subkingdom", "subphylum", "subclass",
                   "infraclass", "superorder", "suborder", "infraorder", "superfamily", "domain"}


def _dotted(kind: str, path: str) -> list[str]:
    """``igneous.coarse`` as ``rock:igneous``, ``rock:igneous.coarse``."""
    parts = path.split(".")
    return [f"{kind}:{'.'.join(parts[: i + 1])}" for i in range(len(parts))]


def taxon_lineage(lineage: Lineage) -> tuple[str, ...]:
    """A backbone taxon: its ancestors from the kingdom down, then the accepted taxon itself."""
    keys = [k for k in lineage.ancestors if k != lineage.effective_key]
    return ("taxon", *(f"taxon:{k}" for k in keys), f"taxon:{lineage.effective_key}")


def term_lineage(kind: str, term: vocab.Term) -> tuple[str, ...]:
    """A resolved rock, mineral, crystal or material anchor."""
    if kind == "mineral":
        nodes = _dotted("mineral", term.path)
        if term.rank == "species":
            nodes.append(f"mineral:{term.path}/{vocab.kebab(term.ref)}")
        return ("mineral", *nodes)
    if kind == "rock":
        return ("rock", *_dotted("rock", term.path), f"rock:{term.path}/{term.ref}")
    if kind == "material":
        return ("material", *_dotted("material", term.path), f"material:{term.path}/{term.ref}")
    if kind == "crystal":
        origin, _, system = term.ref.partition("/")
        nodes = [f"crystal:{origin}"]
        base = origin
        if term.classification:
            base = f"{origin}.{term.classification}"
            nodes.append(f"crystal:{base}")
        if system:
            nodes.append(f"crystal:{base}/{system}")
        return ("crystal", *nodes)
    raise ValueError(f"no lineage for a {kind} anchor")


def kind_of(node: str) -> str:
    return node.split(":", 1)[0]


def is_root(node: str) -> bool:
    return node in ROOTS


@dataclass(frozen=True)
class Depth:
    """Whether a community node is as fine as its kind needs, or as the vote "as good as it can be" allows."""

    enough: bool
    allowed_when_voted: bool


def depth_of(node: str, rank: str | None) -> Depth:
    """How far a community node goes, by its kind: the rule of the badge (R-1304, dossier 15 section 5).

    ``rank`` is the node's rank when it is a taxon (read from the taxon cache), or a mineral node's ``species`` or
    ``group``; the vocabulary kinds are read from the node itself.
    """
    kind = kind_of(node)
    if is_root(node):
        return Depth(False, False)
    if kind == "taxon":
        r = (rank or "").lower()
        return Depth(r in SPECIES_OR_BELOW, bool(r) and r not in FAMILY_OR_ABOVE)
    if kind == "mineral":
        return Depth("/" in node, rank == "group" or "/" in node)
    if kind in ("rock", "material"):
        return Depth("/" in node, "/" in node)
    if kind == "crystal":
        rest = node.split(":", 1)[1]
        finer = "/" in rest or "." in rest
        return Depth(finer, True)
    return Depth(False, False)
