"""The collection tree as the web reads it: node records with slide counts, host views, IIIF Collections.

Counts are of published slides placed at a node or below. A view (Parasites and hosts) counts the published
slides whose recorded host lies inside the view's collection, read with the host's cached lineage.
"""

from __future__ import annotations

import json

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.collections import vocab
from app.collections.rules import Facts
from app.collections.tree import Node, Tree, counts
from app.contracts import catalog as c
from app.db.models import Slide, Taxon
from app.delivery.manifest import PRESENTATION_CONTEXT, collection_url

GBIF_SPECIES = "https://www.gbif.org/species/"


def _text(pair: dict[str, str]) -> c.LocalisedText:
    return c.LocalisedText(en=pair.get("en", ""), es=pair.get("es", ""))


def _taxon_labels(tree: Tree) -> dict[int, tuple[str, str]]:
    return {v["key"]: (v["name"], v["rank"]) for v in tree.taxa.values()}


def strunz_code(path: str) -> str:
    """A mineral path back to the code people know: ``9.A.F.15`` to ``9.AF.15``, ``9.A`` stays."""
    parts = path.split(".")
    code = parts[0]
    if len(parts) > 1:
        code += "." + "".join(parts[1:3])
    if len(parts) > 3:
        code += "." + parts[3]
    return code


def _path_label(kind: str | None, path: str) -> tuple[str, str]:
    """A rule path for people, with the definition kind it belongs to."""
    v = vocab.load()
    if kind == "mineral" or path[:1].isdigit():
        return "mineral", f"Nickel-Strunz {strunz_code(path)}"
    if kind == "crystal" or path.split(".")[0] in v.crystal_origins:
        origin, _, category = path.partition(".")
        label = v.crystal_origins[origin]["en"]
        return "crystal", f"{label}, {v.kikuchi[category]['en']}" if category else label
    if kind == "material" or path in v.material_families:
        return "material", v.material_families[path]["en"]
    return "rock", path.replace(".", ", ").replace("-", " ")


def defined_by(node: Node, tree: Tree) -> list[c.DefinitionRecord]:
    """The node's conditions, as people read them."""
    if node.is_view:
        return [c.DefinitionRecord(kind="relation", value="host",
                                   label="slides whose host lies inside this collection")]
    names = _taxon_labels(tree)
    parts = vocab.load().parts
    out: list[c.DefinitionRecord] = []
    for clause in node.rule.clauses:
        kind = next(iter(clause.kinds)) if clause.kinds and len(clause.kinds) == 1 else None
        if clause.kinds and not clause.taxa and not clause.paths:
            out += [c.DefinitionRecord(kind="kind", value=k, label=k) for k in sorted(clause.kinds)]
        for key in clause.taxa:
            name, rank = names[key]
            out.append(c.DefinitionRecord(kind="taxon", value=str(key), label=f"{name} ({rank})",
                                          url=f"{GBIF_SPECIES}{key}"))
        for key in clause.exclude:
            name, rank = names[key]
            out.append(c.DefinitionRecord(kind="excluded-taxon", value=str(key), label=f"not {name} ({rank})",
                                          url=f"{GBIF_SPECIES}{key}"))
        inherited = kind or next((next(iter(cl.kinds)) for a in reversed(node.ancestors) for cl in a.rule.clauses
                                  if cl.kinds and len(cl.kinds) == 1), None)
        for path in clause.paths:
            what, label = _path_label(inherited, path)
            out.append(c.DefinitionRecord(kind=what, value=path, label=label))
        for part in sorted(clause.parts or ()):
            out.append(c.DefinitionRecord(kind="part", value=part, label=parts[part]["en"]))
        for state in sorted(clause.preservation or ()):
            out.append(c.DefinitionRecord(kind="preservation", value=state, label=state.replace("_", " ")))
    unique: dict[tuple[str, str], c.DefinitionRecord] = {}
    for d in out:
        unique.setdefault((d.kind, d.value), d)
    return list(unique.values())


async def placed_counts(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(select(Slide.placement_node, func.count()).where(Slide.status == "published")
                            .group_by(Slide.placement_node))
    return {node: int(n) for node, n in rows.all()}


async def host_view_slides(db: AsyncSession, tree: Tree, node: Node) -> list[Slide]:
    """Published slides whose host lies inside the view's collection, newest first."""
    rows = (await db.execute(
        select(Slide, Taxon).options(selectinload(Slide.assets))
        .join(Taxon, Taxon.key == cast(Slide.host_ref, Integer))
        .where(Slide.status == "published", Slide.host_ref.is_not(None))
        .order_by(Slide.published_at.desc(), Slide.id.desc())
    )).all()
    collection = node.parent
    out = []
    for slide, taxon in rows:
        key = taxon.accepted_key or taxon.key
        facts = Facts(kind="taxon", key=key, lineage=frozenset(json.loads(taxon.lineage_json)) | {taxon.key, key})
        if collection.accepts_path(facts, tree.lineages):
            out.append(slide)
    return out


def node_record(node: Node, tree: Tree, placed: dict[str, int], views: dict[str, int], depth: int | None) -> \
        c.CollectionNodeRecord:
    if node.is_view:
        count = views.get(node.id, 0)
    else:
        count = sum(n for nid, n in placed.items() if nid == node.id or nid.startswith(node.id + "."))
    children = [] if depth == 0 else [
        node_record(child, tree, placed, views, None if depth is None else depth - 1) for child in node.children
    ]
    return c.CollectionNodeRecord(
        id=node.id, level=node.level, name=_text(node.name), about=_text(node.about), icon=node.icon,
        view=node.is_view, priority=node.rule.priority, defined_by=defined_by(node, tree), slide_count=count,
        children=children,
    )


async def view_counts(db: AsyncSession, tree: Tree) -> dict[str, int]:
    return {n.id: len(await host_view_slides(db, tree, n)) for n in tree.walk() if n.is_view}


async def tree_record(db: AsyncSession, tree: Tree) -> c.CollectionTreeRecord:
    placed, views = await placed_counts(db), await view_counts(db, tree)
    return c.CollectionTreeRecord(realms=[node_record(r, tree, placed, views, None) for r in tree.roots],
                                  counts=counts(tree))


def node_ref(node: Node) -> c.NodeRef:
    return c.NodeRef(id=node.id, name=_text(node.name), icon=node.icon)


async def node_detail(db: AsyncSession, tree: Tree, node: Node, base: str) -> c.CollectionNodeDetail:
    placed = await placed_counts(db)
    views = {n.id: len(await host_view_slides(db, tree, n)) for n in [node, *node.children] if n.is_view}
    return c.CollectionNodeDetail(
        node=node_record(node, tree, placed, views, 1),
        path=[node_ref(n) for n in node.ancestors + [node]],
        iiif_collection_url=collection_url(base, node.id),
    )


def _label(pair: dict[str, str]) -> dict[str, list[str]]:
    return {lang: [text] for lang, text in pair.items() if text}


async def iiif_collection(db: AsyncSession, tree: Tree, node: Node, base: str) -> dict:
    """The node as a IIIF Presentation 3 Collection: its child nodes, then the manifests of the slides placed
    directly at it (for a view, the slides it shows)."""
    base = base.rstrip("/")
    items: list[dict] = [{"id": collection_url(base, child.id), "type": "Collection", "label": _label(child.name)}
                         for child in node.children]
    if node.is_view:
        slides = await host_view_slides(db, tree, node)
    else:
        slides = list((await db.execute(
            select(Slide).where(Slide.status == "published", Slide.placement_node == node.id)
            .order_by(Slide.published_at.desc(), Slide.id.desc())
        )).scalars().all())
    items += [{"id": f"{base}/api/slides/{s.short_id}/manifest", "type": "Manifest",
               "label": {"none": [f"{s.anchor_name}, {s.short_id}"]}} for s in slides]
    document = {
        "@context": PRESENTATION_CONTEXT,
        "id": collection_url(base, node.id),
        "type": "Collection",
        "label": _label(node.name),
        "summary": _label(node.about),
        "items": items,
    }
    if node.parent is not None:
        document["partOf"] = [{"id": collection_url(base, node.parent.id), "type": "Collection",
                               "label": _label(node.parent.name)}]
    return document


def facets() -> list[c.FacetRecord]:
    v = vocab.load()

    def values(prefix: str, entries: dict[str, dict]) -> list[c.FacetValueRecord]:
        return [c.FacetValueRecord(id=k, name=_text(e), icon=f"facet.{prefix}.{k}") for k, e in entries.items()]

    organs = {k: t for k, t in v.parts.items() if t.get("facet")}
    return [
        c.FacetRecord(id="preparation", name=c.LocalisedText(en="Preparation", es="Preparación"),
                      values=values("preparation", v.preparations)),
        c.FacetRecord(id="modality", name=c.LocalisedText(en="Imaging modality", es="Modalidad de imagen"),
                      values=values("modality", v.modalities)),
        c.FacetRecord(id="plant-organ", name=c.LocalisedText(en="Plant organ", es="Órgano vegetal"),
                      values=values("plant-organ", organs)),
        c.FacetRecord(id="crystal-system", name=c.LocalisedText(en="Crystal system", es="Sistema cristalino"),
                      values=values("crystal-system", v.crystal_systems)),
    ]


def facet_icons() -> set[str]:
    return {value.icon for facet in facets() for value in facet.values}
