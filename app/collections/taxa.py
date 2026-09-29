"""The lineage of a taxon anchor, from the GBIF backbone, cached in the ``taxon`` table.

A slide names its taxon by GBIF usage key. Placement needs the keys of the taxon's ancestors, which the GBIF API
gives (``/v1/species/{key}`` for the record, ``/v1/species/{key}/parents`` for the lineage). The first time a key is
seen both are read and stored; afterwards placement uses the stored row and never waits on the network, and a
slide's placement can be recomputed years later with the lineage it was placed with.

A key must belong to the backbone (dataset ``d7dddbf4-...``): GBIF also serves keys of other checklists, which
the tree's rules do not speak about. A synonym is followed to its accepted taxon, whose lineage is used.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import httpx2
from sqlalchemy.ext.asyncio import AsyncSession

from app.collections.rules import Facts
from app.db.models import Taxon

BACKBONE = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"
USER_AGENT = "Laminario (https://github.com/fsantibanezleal/CAOS_Laminario)"


class TaxonServiceUnavailable(RuntimeError):
    """GBIF did not answer; the submission can be retried."""


@dataclass(frozen=True)
class Lineage:
    key: int
    name: str
    rank: str
    status: str
    accepted_key: int | None
    ancestors: tuple[int, ...]

    @property
    def effective_key(self) -> int:
        return self.accepted_key or self.key

    @property
    def keys(self) -> frozenset[int]:
        """The taxon, its accepted taxon and every ancestor: what a rule's taxa are looked for in."""
        return frozenset(self.ancestors) | {self.key, self.effective_key}

    def facts(self, part: str | None = None, preservation: str = "recent") -> Facts:
        return Facts(kind="taxon", key=self.effective_key, lineage=self.keys, part=part, preservation=preservation)


def _row_lineage(row: Taxon) -> Lineage:
    return Lineage(row.key, row.name, row.rank, row.status, row.accepted_key, tuple(json.loads(row.lineage_json)))


def new_client(base_url: str) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(base_url=base_url.rstrip("/"), timeout=15.0, headers={"User-Agent": USER_AGENT})


async def _get(client: httpx2.AsyncClient, path: str, params: dict | None = None) -> dict | list | None:
    try:
        response = await client.get(path, params=params)
    except httpx2.HTTPError as exc:
        raise TaxonServiceUnavailable(f"GBIF did not answer: {exc}") from exc
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise TaxonServiceUnavailable(f"GBIF answered {response.status_code}")
    return response.json()


async def fetch(client: httpx2.AsyncClient, key: int) -> Lineage | None:
    """Read a backbone taxon and its lineage from GBIF; ``None`` for a key that is not a backbone taxon."""
    record = await _get(client, f"/species/{key}")
    if not isinstance(record, dict) or record.get("datasetKey") != BACKBONE:
        return None
    status = str(record.get("taxonomicStatus", "")).lower()
    accepted = record.get("acceptedKey") if "synonym" in status else None
    parents = await _get(client, f"/species/{accepted or key}/parents")
    return Lineage(
        key=key,
        name=record.get("canonicalName") or record.get("scientificName") or str(key),
        rank=str(record.get("rank", "")).lower(),
        status="synonym" if "synonym" in status else status or "accepted",
        accepted_key=accepted,
        ancestors=tuple(p["key"] for p in parents or []),
    )


async def lineage(db: AsyncSession, client: httpx2.AsyncClient, key: int) -> Lineage | None:
    """The cached lineage of a key, fetched and stored on first use."""
    row = await db.get(Taxon, key)
    if row is not None:
        return _row_lineage(row)
    found = await fetch(client, key)
    if found is None:
        return None
    existing = await db.get(Taxon, key)  # another request may have stored it meanwhile
    if existing is None:
        db.add(Taxon(key=found.key, name=found.name, rank=found.rank, status=found.status,
                     accepted_key=found.accepted_key, lineage_json=json.dumps(list(found.ancestors))))
        await db.flush()
    return found


async def suggest(client: httpx2.AsyncClient, query: str, limit: int = 10) -> list[dict]:
    """Backbone names that start with the query, for the anchor field (GBIF's suggest service)."""
    found = await _get(client, "/species/suggest", {"datasetKey": BACKBONE, "limit": limit, "q": query})
    out = []
    for item in found or []:
        higher = [item.get(r) for r in ("kingdom", "phylum", "class", "order", "family") if item.get(r)]
        out.append({"ref": str(item["key"]), "name": item.get("canonicalName") or item.get("scientificName"),
                    "rank": str(item.get("rank", "")).lower() or None, "classification": None,
                    "context": " > ".join(higher)})
    return out
