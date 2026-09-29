"""Search over slides with SQLite FTS5 (dossier 12, section 4).

Each slide carries ``search_text``, composed here when the slide is created or its placement changes: the anchor's
name and the determination as written, the host's name, the catalogue number and short id, the locality and the
country's English and Spanish names, the names of every node on the slide's placement path in both languages, and the
preparation's and the stain's names. Migration 0008 keeps the FTS5 table ``slide_search`` in step with that column by
triggers (external content, tokenizer ``unicode61 remove_diacritics 2``, so "liquenes" finds "líquenes"), so the index
never drifts from the rows, whatever writes them (the API, the bake, the import).

A query is turned into an FTS5 expression of quoted prefix terms joined by AND, so a visitor's text is never parsed as
FTS5 syntax; results are ranked by BM25.

``reindex`` composes the text again for every slide (or the slides named): migration 0008 runs it for the slides that
existed before the column, and the base import runs it for the slides it loads, since a bake's rows carry the text
composed with the tree of their day.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from sqlalchemy import Connection, text

from app.collections import places, vocab
from app.collections.tree import Tree, load_tree

FTS_TABLES = ("slide_search", "slide_search_data", "slide_search_idx", "slide_search_docsize", "slide_search_config")
TOKEN = re.compile(r"[\w.\-]+", re.UNICODE)


def compose(*, short_id: str, anchor_name: str, host_name: str | None, catalogue_number: str | None,
            locality_text: str | None, country: str | None, placement_node: str, preparation: str,
            stain: str | None, tree: Tree | None = None) -> str:
    tree = tree or load_tree()
    parts: list[str] = [anchor_name, short_id]
    for value in (host_name, catalogue_number, locality_text, stain):
        if value:
            parts.append(value)
    if country and places.known(country):
        parts += [places.name(country, "en"), places.name(country, "es"), country]
    node = tree.get(placement_node)
    while node is not None:
        parts += [node.name["en"], node.name["es"]]
        node = node.parent
    names = vocab.load().preparations.get(preparation)
    if names:
        parts += [names["en"], names["es"]]
    return " | ".join(dict.fromkeys(p.strip() for p in parts if p and p.strip()))


def fts_query(text: str) -> str | None:
    """The visitor's words as an FTS5 expression: each word a quoted prefix term, all required."""
    words = [w.replace('"', "") for w in TOKEN.findall(text or "")]
    words = [w for w in words if w]
    if not words:
        return None
    return " AND ".join(f'"{w}"*' for w in words[:12])


def reindex(conn: Connection, short_ids: Iterable[str] | None = None) -> int:
    """Compose ``search_text`` again (and a missing country from the coordinates) for every slide, or for the slides
    named; the triggers carry the new text into the index. Returns how many slides were written."""
    tree = load_tree()
    rows = conn.execute(text(
        "SELECT id, short_id, anchor_name, host_name, catalogue_number, locality_text, country, lat, lon, "
        "placement_node, preparation, stain FROM slide")).mappings().all()
    wanted = set(short_ids) if short_ids is not None else None
    written = 0
    for row in rows:
        if wanted is not None and row["short_id"] not in wanted:
            continue
        country = row["country"]
        if country is None and row["lat"] is not None and row["lon"] is not None:
            country = places.locate(row["lat"], row["lon"])
        composed = compose(short_id=row["short_id"], anchor_name=row["anchor_name"], host_name=row["host_name"],
                           catalogue_number=row["catalogue_number"], locality_text=row["locality_text"],
                           country=country, placement_node=row["placement_node"], preparation=row["preparation"],
                           stain=row["stain"], tree=tree)
        conn.execute(text("UPDATE slide SET search_text = :t, country = :c WHERE id = :i"),
                     {"t": composed, "c": country, "i": row["id"]})
        written += 1
    return written
