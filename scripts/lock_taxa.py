"""Resolve every taxon the collection tree names against the GBIF backbone, and lock the result.

The tree names taxa as ``Name@rank`` (``Aves@class``). Each is matched with ``/v1/species/match`` (strict, with the
rank), must come back EXACT at that rank and ACCEPTED (DOUBTFUL is accepted with a note: the backbone keeps a few
protist classes so), and its lineage is read from ``/v1/species/{key}/parents``. The lock file stores key, name,
rank, status and the lineage keys, so placement never needs the network for the tree itself.

    python scripts/lock_taxa.py            # resolve and write app/collections/data/taxa.lock.json
    python scripts/lock_taxa.py --check    # resolve again and report any difference from the lock

A name that does not resolve stops the script: the tree must then name the taxon the backbone uses (dossier 09:
the backbone has no Phthiraptera, no Actinopterygii and no Reptilia, so the tree names their parts).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import httpx2
import yaml

ROOT = Path(__file__).resolve().parent.parent
TREE = ROOT / "app" / "collections" / "data" / "tree.yaml"
LOCK = ROOT / "app" / "collections" / "data" / "taxa.lock.json"
API = "https://api.gbif.org/v1"
BACKBONE = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"
USER_AGENT = "Laminario taxa lock (https://github.com/fsantibanezleal/CAOS_Laminario)"


def tree_taxa() -> list[str]:
    """Every Name@rank the tree uses, in first-seen order."""
    found: dict[str, None] = {}

    def flat(specs: list) -> list[str]:
        return [s for item in specs for s in (flat(item) if isinstance(item, list) else [item])]

    def rule(r: dict | None) -> None:
        if not r:
            return
        for spec in flat((r.get("taxa") or []) + (r.get("exclude") or [])):
            found.setdefault(spec, None)
        for alt in r.get("any") or []:
            rule(alt)

    def walk(nodes: list[dict]) -> None:
        for n in nodes:
            rule(n.get("rule"))
            walk(n.get("children") or [])

    data = yaml.safe_load(TREE.read_text(encoding="utf-8"))
    for shared in (data.get("shared") or {}).values():
        walk(shared)
    walk(data["nodes"])
    return list(found)


def resolve(client: httpx2.Client, spec: str) -> dict:
    name, _, rank = spec.partition("@")
    match = client.get(f"{API}/species/match", params={"name": name, "rank": rank.upper(), "strict": "true"}).json()
    if match.get("matchType") != "EXACT" or match.get("rank") != rank.upper():
        raise SystemExit(f"{spec}: no exact match at rank {rank} (got {match.get('matchType')} {match.get('rank')})")
    if match.get("status") not in ("ACCEPTED", "DOUBTFUL"):
        raise SystemExit(f"{spec}: status {match.get('status')}; name the accepted taxon instead")
    key = match["usageKey"]
    parents = client.get(f"{API}/species/{key}/parents").json()
    return {"key": key, "name": match.get("canonicalName") or name, "rank": match["rank"].lower(),
            "status": match["status"].lower(), "lineage": [p["key"] for p in parents]}


def build() -> dict:
    taxa = {}
    with httpx2.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        for spec in tree_taxa():
            taxa[spec] = resolve(client, spec)
            time.sleep(0.1)
    return {"about": "GBIF backbone keys and lineages of the taxa the collection tree names. "
                     "Built by scripts/lock_taxa.py; the backbone is CC BY 4.0.",
            "backbone": {"dataset": BACKBONE, "api": API, "resolved_on": date.today().isoformat()},
            "taxa": taxa}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report differences from the committed lock")
    args = parser.parse_args()
    data = build()
    if args.check:
        old = json.loads(LOCK.read_text(encoding="utf-8"))["taxa"]
        changed = [s for s in set(old) | set(data["taxa"]) if old.get(s) != data["taxa"].get(s)]
        for spec in sorted(changed):
            print(f"{spec}: locked {old.get(spec)} now {data['taxa'].get(spec)}")
        print(f"{len(data['taxa'])} taxa, {len(changed)} differ from the lock")
        return 1 if changed else 0
    LOCK.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(data['taxa'])} taxa locked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
