"""The collection tree: browse it, look up anchors, and ask where a slide belongs.

| Route | What |
|---|---|
| `GET /api/collections` | the whole tree with published-slide counts |
| `GET /api/collections/{id}` | one node with its children and the path down to it |
| `GET /api/collections/{id}/iiif` | the node as a IIIF Presentation 3 Collection (the `partOf` of every manifest) |
| `GET /api/facets` | preparation, modality, plant organ and crystal system, with their icons |
| `GET /api/anchors/search?kind=&q=` | names for the anchor field: GBIF backbone taxa or a vocabulary |
| `POST /api/placement` | the suggested node for an anchor, and every node that accepts it |
| `GET /api/vocab/parts` | the parts of an organism a slide can show, by organ system |
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.collections import taxa, vocab
from app.collections.placement import place
from app.collections.service import resolve_anchor
from app.collections.tree import load_tree
from app.contracts import catalog as c
from app.contracts.ingest import Anchor, Preservation
from app.db.session import session
from app.delivery.manifest import MANIFEST_MEDIA_TYPE
from app.services import collections as svc

router = APIRouter(prefix="/api", tags=["collections"])
NODE_ID = r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:-[a-z0-9]+)*)*$"
Db = Annotated[AsyncSession, Depends(session)]


class PlacementQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchor: Anchor
    part: str | None = None
    preservation: Preservation = "recent"


def _node(node_id: str):
    node = load_tree().get(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="no such collection node")
    return node


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=f"the GBIF taxonomy did not answer; try again ({exc})")


@router.get("/collections", response_model=c.CollectionTreeRecord)
async def read_tree(db: Db) -> c.CollectionTreeRecord:
    """The three realms and everything under them, with the published slides of each node counted."""
    return await svc.tree_record(db, load_tree())


@router.get("/collections/{node_id}", response_model=c.CollectionNodeDetail)
async def read_node(node_id: str, request: Request, db: Db) -> c.CollectionNodeDetail:
    """One node, its children, and the path from its realm."""
    return await svc.node_detail(db, load_tree(), _node(node_id), request.app.state.settings.public_base_url)


@router.get("/collections/{node_id}/iiif")
async def read_iiif_collection(node_id: str, request: Request, db: Db) -> JSONResponse:
    """The node as a IIIF Presentation 3 Collection, for any IIIF viewer or aggregator."""
    document = await svc.iiif_collection(db, load_tree(), _node(node_id), request.app.state.settings.public_base_url)
    return JSONResponse(document, media_type=MANIFEST_MEDIA_TYPE, headers={"Access-Control-Allow-Origin": "*"})


@router.get("/vocab/parts", response_model=list[c.PartRecord])
def read_parts() -> list[c.PartRecord]:
    """The parts vocabulary in its file's order (grouped by organ system), each name in English and Spanish."""
    return [c.PartRecord(id=key, group=term["group"], name=c.LocalisedText(en=term["en"], es=term["es"]))
            for key, term in vocab.load().parts.items()]


@router.get("/facets", response_model=list[c.FacetRecord])
def read_facets() -> list[c.FacetRecord]:
    """The properties that cut across the tree, each value with its icon."""
    return svc.facets()


@router.get("/anchors/search", response_model=list[c.AnchorSuggestion])
async def search_anchors(
    request: Request,
    kind: Annotated[Literal["taxon", "rock", "mineral", "crystal", "material"], Query()],
    q: Annotated[str, Query(min_length=2, max_length=80)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[c.AnchorSuggestion]:
    """Names the anchor field can offer: backbone taxa from GBIF, or entries of a vocabulary."""
    if kind == "taxon":
        try:
            found = await taxa.suggest(request.app.state.gbif_client, q, limit=min(limit, 20))
        except taxa.TaxonServiceUnavailable as exc:
            raise _unavailable(exc) from exc
    else:
        found = vocab.search(kind, q, limit)
    return [c.AnchorSuggestion(**item) for item in found]


@router.post("/placement", response_model=c.PlacementResult)
async def suggest_placement(query: PlacementQuery, request: Request, db: Db) -> c.PlacementResult:
    """Where a slide with this anchor belongs: the suggested node, the path to it, and every node that accepts it."""
    problem = vocab.check_part(query.part)
    if problem:
        return c.PlacementResult(errors=[c.ValidationError(field=problem.field, message=problem.message,
                                                           expected=problem.expected, code=problem.code,
                                                           params=problem.params)])
    try:
        resolved = await resolve_anchor(db, request.app.state.gbif_client, query.anchor, part=query.part,
                                        preservation=query.preservation, at="anchor")
    except taxa.TaxonServiceUnavailable as exc:
        raise _unavailable(exc) from exc
    await db.commit()
    if isinstance(resolved, dict):
        return c.PlacementResult(errors=[c.ValidationError(**resolved)])
    tree = load_tree()
    placed = place(resolved.facts, tree)
    anchor = c.AnchorRecord(kind=query.anchor.kind, ref=resolved.ref, name=query.anchor.name, rank=resolved.rank,
                            classification=resolved.classification)
    return c.PlacementResult(anchor=anchor, suggestion=placed.suggestion,
                             path=[svc.node_ref(tree.get(n)) for n in placed.path], accepting=list(placed.accepting))
