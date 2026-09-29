"""The community on a synchronous connection: the API (through ``run_sync``), the worker at publication, the base
import and the backfill command.

It reads taxon lineages from the ``taxon`` cache only, never the network (the API caches a missing ancestor before it
calls ``refresh``). ``first_identification`` makes a slide's own identification (its contributor's, or its source's
for a base slide, R-1309); ``source_determination`` records a base slide's changed determination after an import;
``refresh`` computes the community, clears the votes when its node changes, makes the slide follow a community anchor
Laminario can name (R-1303) and computes the badge (R-1304).
"""

from __future__ import annotations

import json
import logging
import secrets
import uuid
from dataclasses import dataclass
from types import SimpleNamespace

from sqlalchemy import Connection, text

from app.collections import vocab
from app.collections.placement import place
from app.collections.rules import Facts
from app.collections.taxa import Lineage
from app.collections.tree import load_tree
from app.community.agreement import Community, Ident, community
from app.community.lineage import kind_of, taxon_lineage, term_lineage
from app.community.quality import badge
from app.db.base import utcnow

log = logging.getLogger(__name__)


def cached_lineage(conn: Connection, key: int) -> Lineage | None:
    row = conn.execute(text("SELECT key, name, rank, status, accepted_key, lineage_json FROM taxon WHERE key = :k"),
                       {"k": key}).one_or_none()
    if row is None:
        return None
    return Lineage(row.key, row.name, row.rank, row.status, row.accepted_key, tuple(json.loads(row.lineage_json)))


def lineage_of(conn: Connection, kind: str, ref: str, classification: str | None) -> tuple[str, ...] | None:
    """An anchor's lineage from the cache and the vocabularies; None when a taxon is not cached."""
    if kind == "taxon":
        found = cached_lineage(conn, int(ref)) if ref.isdigit() else None
        return taxon_lineage(found) if found else None
    term = vocab.resolve_term(kind, ref, classification)
    if isinstance(term, vocab.Problem):
        return None
    return term_lineage(kind, term)


def _insert(conn: Connection, slide_id: int, user: str | None, anchor, lineage: tuple[str, ...], when) -> None:
    conn.execute(text(
        "INSERT INTO identification (public_id, slide_id, user_id, anchor_kind, anchor_ref, anchor_name, anchor_rank, "
        "anchor_classification, lineage_json, previous_lineage_json, disagreement, body, current, hidden, created_at, "
        "updated_at) VALUES (:p, :s, :u, :k, :r, :n, :rank, :c, :l, NULL, NULL, NULL, 1, 0, :t, :t)"),
        {"p": secrets.token_hex(12), "s": slide_id, "u": str(uuid.UUID(user)) if user else None,
         "k": anchor.anchor_kind, "r": anchor.anchor_ref, "n": anchor.anchor_name, "rank": anchor.anchor_rank,
         "c": anchor.anchor_classification, "l": json.dumps(list(lineage)), "t": when})


def _slide(conn: Connection, slide_id: int):
    return conn.execute(text(
        "SELECT id, short_id, origin, status, contributor_id, anchor_kind, anchor_ref, anchor_name, anchor_rank, "
        "anchor_classification, part, preservation, placement_node, placement_override_reason, community_node, "
        "community_rank, published_at, created_at FROM slide WHERE id = :s"), {"s": slide_id}).one()


def first_identification(conn: Connection, slide_id: int) -> bool:
    """Make the slide's own identification when it has none: its contributor's anchor, or its source's determination.
    Returns whether one was made."""
    if conn.execute(text("SELECT 1 FROM identification WHERE slide_id = :s LIMIT 1"), {"s": slide_id}).first():
        return False
    s = _slide(conn, slide_id)
    lineage = lineage_of(conn, s.anchor_kind, s.anchor_ref, s.anchor_classification)
    if lineage is None:
        log.warning("slide %s: the anchor %s %s has no cached lineage; no first identification", s.short_id,
                    s.anchor_kind, s.anchor_ref)
        return False
    user = s.contributor_id if s.origin == "contribution" else None
    if user is not None:
        try:
            uuid.UUID(user)
        except ValueError:
            log.warning("slide %s: its contributor id %r is no account's; no first identification", s.short_id, user)
            return False
    _insert(conn, slide_id, user, s, lineage, s.published_at or s.created_at or utcnow())
    return True


def source_determination(conn: Connection, slide_id: int, anchor) -> bool:
    """After an import: when the source's determination (``anchor``: the bake's anchor columns) differs from the
    source's current identification, it becomes the current one. Returns whether it changed."""
    current = conn.execute(text("SELECT id, anchor_kind, anchor_ref FROM identification WHERE slide_id = :s AND "
                                "user_id IS NULL AND current = 1"), {"s": slide_id}).first()
    if current is not None and (current.anchor_kind, current.anchor_ref) == (anchor.anchor_kind, anchor.anchor_ref):
        return False
    lineage = lineage_of(conn, anchor.anchor_kind, anchor.anchor_ref, anchor.anchor_classification)
    if lineage is None:
        return False
    conn.execute(text("UPDATE identification SET current = 0 WHERE slide_id = :s AND user_id IS NULL"),
                 {"s": slide_id})
    _insert(conn, slide_id, None, anchor, lineage, utcnow())
    return True


def idents_of(conn: Connection, slide_id: int) -> list[Ident]:
    rows = conn.execute(text(
        "SELECT id, user_id, lineage_json, previous_lineage_json, disagreement, current, hidden FROM identification "
        "WHERE slide_id = :s ORDER BY id"), {"s": slide_id}).all()
    return [Ident(order=r.id, account=str(r.user_id) if r.user_id else "source",
                  lineage=tuple(json.loads(r.lineage_json)), current=bool(r.current), hidden=bool(r.hidden),
                  disagreement=None if r.disagreement is None else bool(r.disagreement),
                  previous=tuple(json.loads(r.previous_lineage_json)) if r.previous_lineage_json else None)
            for r in rows]


def checks_pass(conn: Connection, slide_id: int, origin: str) -> bool:
    from app.services.catalog import quality_checks

    rows = conn.execute(text(
        "SELECT family, licence_uri, source_url, pixel_size_um, modality FROM asset WHERE slide_id = :s"),
        {"s": slide_id}).all()
    assets = [SimpleNamespace(**r._mapping) for r in rows]
    return all(check.passed for check in quality_checks(origin, assets))


def votes(conn: Connection, slide_id: int) -> tuple[int, int]:
    """(as good as it can be, still needs identification)."""
    rows = conn.execute(text("SELECT as_good_as_it_can_be, COUNT(*) AS n FROM slide_vote WHERE slide_id = :s "
                             "GROUP BY as_good_as_it_can_be"), {"s": slide_id}).all()
    counts = {bool(r.as_good_as_it_can_be): r.n for r in rows}
    return counts.get(True, 0), counts.get(False, 0)


@dataclass(frozen=True)
class NodeAnchor:
    anchor_kind: str
    anchor_ref: str
    anchor_name: str
    anchor_rank: str | None
    anchor_classification: str | None


def node_anchor(conn: Connection, node: str) -> NodeAnchor | None:
    """The anchor a community node names: a current identification of exactly that node, or, for a taxon, its cached
    backbone record; None for a node that is not an anchor (a rock family, a Nickel-Strunz class)."""
    for row in conn.execute(text(
            "SELECT anchor_kind, anchor_ref, anchor_name, anchor_rank, anchor_classification, lineage_json "
            "FROM identification WHERE current = 1 AND hidden = 0 AND lineage_json LIKE :tail ORDER BY id"),
            {"tail": f'%"{node}"]'}).all():
        if json.loads(row.lineage_json)[-1] == node:
            return NodeAnchor(row.anchor_kind, row.anchor_ref, row.anchor_name, row.anchor_rank,
                              row.anchor_classification)
    if kind_of(node) == "taxon":
        found = cached_lineage(conn, int(node.split(":", 1)[1]))
        if found is not None:
            return NodeAnchor("taxon", str(found.effective_key), found.name, found.rank, None)
    return None


def _facts(conn: Connection, target: NodeAnchor, part: str | None, preservation: str) -> Facts | None:
    if target.anchor_kind == "taxon":
        found = cached_lineage(conn, int(target.anchor_ref))
        return found.facts(part, preservation) if found else None
    term = vocab.resolve_term(target.anchor_kind, target.anchor_ref, target.anchor_classification)
    if isinstance(term, vocab.Problem):
        return None
    return Facts(kind=target.anchor_kind, path=term.path, part=part, preservation=preservation)


def follow(conn: Connection, slide_id: int, target: NodeAnchor) -> bool:
    """The slide takes the community anchor, and the tree places it again, keeping a drawer that still accepts it and
    a curator's override (R-1303). Returns whether the anchor changed."""
    from app.services import search

    s = _slide(conn, slide_id)
    if (s.anchor_kind, s.anchor_ref) == (target.anchor_kind, target.anchor_ref):
        return False
    taxon = target.anchor_kind == "taxon"
    part = s.part if taxon else None
    preservation = s.preservation if taxon else "recent"
    node = s.placement_node
    facts = _facts(conn, target, part, preservation)
    if facts is not None and not s.placement_override_reason:
        placed = place(facts, load_tree())
        if node not in placed.accepting and placed.suggestion:
            node = placed.suggestion
    conn.execute(text(
        "UPDATE slide SET anchor_kind = :k, anchor_ref = :r, anchor_name = :n, anchor_rank = :rank, "
        "anchor_classification = :c, part = :part, preservation = :pres, placement_node = :node, updated_at = :t"
        + ("" if taxon else ", host_ref = NULL, host_name = NULL, host_rank = NULL") + " WHERE id = :s"),
        {"k": target.anchor_kind, "r": target.anchor_ref, "n": target.anchor_name, "rank": target.anchor_rank,
         "c": target.anchor_classification, "part": part, "pres": preservation, "node": node, "t": utcnow(),
         "s": slide_id})
    search.reindex(conn, [s.short_id])
    return True


def refresh(conn: Connection, slide_id: int) -> Community:
    """The community, the slide following it, and the badge, from what is stored."""
    s = _slide(conn, slide_id)
    result = community(idents_of(conn, slide_id))
    rank = s.community_rank
    if result.node != s.community_node:
        conn.execute(text("DELETE FROM slide_vote WHERE slide_id = :s"), {"s": slide_id})
        rank = None
    if result.node is not None:
        target = node_anchor(conn, result.node)
        if target is not None:
            rank = target.anchor_rank
            follow(conn, slide_id, target)
    as_good, needs_more = votes(conn, slide_id)
    value = badge(checks_pass(conn, slide_id, s.origin), result.node, rank, as_good, needs_more)
    conn.execute(text("UPDATE slide SET community_node = :n, community_rank = :r, badge = :b WHERE id = :s"),
                 {"n": result.node, "r": rank, "b": value, "s": slide_id})
    return result


def backfill(conn: Connection) -> dict[str, int]:
    """Every published or hidden slide gets its first identification, and its community and badge (idempotent)."""
    made = 0
    ids = [r.id for r in conn.execute(text(
        "SELECT id FROM slide WHERE status IN ('published', 'hidden') ORDER BY id")).all()]
    for slide_id in ids:
        made += first_identification(conn, slide_id)
        refresh(conn, slide_id)
    return {"slides": len(ids), "identifications": made}
