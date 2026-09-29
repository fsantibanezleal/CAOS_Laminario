"""The tree's part of accepting a submission: resolve the anchor, and check where it is placed.

After the ingestion contract has passed, ``check_submission``:

1. resolves the anchor: a taxon through the GBIF cache (``taxa``), anything else through its vocabulary
   (``vocab``), giving the canonical reference, rank, classification and the facts placement needs;
2. checks the part against the parts vocabulary and resolves the host, whose lineage the Parasites and hosts views
   read;
3. checks the placement: the node must exist, must not be a view, and must accept the slide, unless a curator
   overrides with a reason (the router refuses an override from anyone else).

Every problem is returned in the contract's error shape (field, message, expected). ``TaxonServiceUnavailable``
propagates: the caller answers 503, because the submission is not wrong, GBIF is just not answering.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx2
from sqlalchemy.ext.asyncio import AsyncSession

from app.collections import taxa, vocab
from app.collections.placement import Placement, place
from app.collections.rules import Facts
from app.collections.tree import Tree, load_tree
from app.contracts.ingest import Anchor, SlideCaseSubmission

SHOWN_NODES = 6


@dataclass
class ResolvedAnchor:
    ref: str
    rank: str | None
    classification: str | None
    facts: Facts


@dataclass
class Checked:
    errors: list[dict[str, str]] = field(default_factory=list)
    anchor: ResolvedAnchor | None = None
    placement: Placement | None = None


def _error(field_name: str, message: str, expected: str) -> dict[str, str]:
    return {"field": field_name, "message": message, "expected": expected}


async def resolve_anchor(db: AsyncSession, client: httpx2.AsyncClient, anchor: Anchor, *, part: str | None,
                         preservation: str, at: str = "specimen.anchor") -> ResolvedAnchor | dict[str, str]:
    """The anchor's canonical form and placement facts, or the error that says why it does not resolve."""
    if anchor.kind == "taxon":
        if not anchor.ref.isdigit():
            return _error(f"{at}.ref", "a taxon is referenced by its GBIF usage key", "the GBIF usage key, digits only")
        found = await taxa.lineage(db, client, int(anchor.ref))
        if found is None:
            return _error(f"{at}.ref", f"{anchor.ref} is not a taxon of the GBIF backbone",
                          "the usage key of a GBIF backbone taxon")
        return ResolvedAnchor(anchor.ref, anchor.rank or found.rank, None, found.facts(part, preservation))
    term = vocab.resolve_term(anchor.kind, anchor.ref, anchor.classification, field=at)
    if isinstance(term, vocab.Problem):
        return _error(term.field, term.message, term.expected)
    facts = Facts(kind=anchor.kind, path=term.path, part=part, preservation=preservation)
    return ResolvedAnchor(term.ref, term.rank or anchor.rank, term.classification, facts)


def node_list(ids: tuple[str, ...]) -> str:
    shown = ", ".join(ids[:SHOWN_NODES])
    return shown + (f" and {len(ids) - SHOWN_NODES} more" if len(ids) > SHOWN_NODES else "")


async def check_submission(db: AsyncSession, client: httpx2.AsyncClient, sub: SlideCaseSubmission, *,
                           tree: Tree | None = None) -> Checked:
    tree = tree or load_tree()
    out = Checked()
    sp = sub.specimen
    problem = vocab.check_part(sp.part)
    if problem:
        out.errors.append(_error(problem.field, problem.message, problem.expected))
    resolved = await resolve_anchor(db, client, sp.anchor, part=sp.part, preservation=sp.preservation)
    if isinstance(resolved, dict):
        out.errors.append(resolved)
    else:
        out.anchor = resolved
    if sp.host is not None and sp.host.kind == "taxon" and sp.host.ref.isdigit():
        if await taxa.lineage(db, client, int(sp.host.ref)) is None:
            out.errors.append(_error("specimen.host.ref", f"{sp.host.ref} is not a taxon of the GBIF backbone",
                                     "the usage key of a GBIF backbone taxon"))
    node = tree.get(sub.placement.node)
    if node is None:
        out.errors.append(_error("placement.node", f"{sub.placement.node} is not a node of the collection tree",
                                 "a node id such as life.birds.feathers"))
    elif node.is_view:
        out.errors.append(_error("placement.node", f"{node.id} is a view of slides placed elsewhere",
                                 "a collection node that holds slides"))
    if out.anchor is not None:
        out.placement = place(out.anchor.facts, tree)
        if node is not None and not node.is_view and node.id not in out.placement.accepting \
                and not sub.placement.override_reason:
            accepting = out.placement.accepting
            expected = (f"{out.placement.suggestion} (suggested), or one of: {node_list(accepting)}"
                        if accepting else "no node takes this anchor; a curator can place it with a reason")
            out.errors.append(_error("placement.node", f"{node.id} does not take this {sp.anchor.kind}", expected))
    return out
