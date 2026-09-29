"""Scientific names chosen at curation, resolved to GBIF backbone keys once and kept (``data/base/names.json``).

A curator writes ``Spirogyra@genus`` (the name as the category or the record gives it, with its rank, and a kingdom
when the name is a homonym: ``Peziza@genus@Fungi``); the key is
looked up with the strict match and must come back EXACT and ACCEPTED (or DOUBTFUL) at that rank, as the tree's
own taxa are (``scripts/lock_taxa.py``). A name that does not resolve stops the build: the curator names the taxon
the backbone uses.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.base.http import Polite

MATCH = "https://api.gbif.org/v1/species/match"
ROOT = Path(__file__).resolve().parent.parent.parent
NAMES = ROOT / "data" / "base" / "names.json"


class NameError_(ValueError):
    pass


def load() -> dict[str, dict]:
    return json.loads(NAMES.read_text(encoding="utf-8")) if NAMES.exists() else {}


def save(names: dict[str, dict]) -> None:
    NAMES.write_text(json.dumps(dict(sorted(names.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8",
                     newline="\n")


def resolve(http: Polite, spec: str, names: dict[str, dict]) -> dict:
    """The backbone key of ``Name@rank``, from the cache or the match service."""
    if spec in names:
        return names[spec]
    if spec.startswith("#"):
        # A backbone key given directly, for a name the match service cannot tell apart (a homonym within a kingdom).
        record = http.json(f"https://api.gbif.org/v1/species/{int(spec[1:])}")
        if record.get("datasetKey") != "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c":
            raise NameError_(f"{spec}: not a backbone key")
        names[spec] = {"key": record["key"], "name": record.get("canonicalName") or record.get("scientificName"),
                       "rank": str(record.get("rank", "")).lower(),
                       "status": str(record.get("taxonomicStatus", "")).lower()}
        return names[spec]
    name, _, rest = spec.partition("@")
    rank, _, kingdom = rest.partition("@")
    params = {"name": name, "strict": "true"}
    if rank:
        params["rank"] = rank.upper()
    if kingdom:
        params["kingdom"] = kingdom
    m = http.json(MATCH, params)
    if m.get("matchType") != "EXACT" or (rank and m.get("rank") != rank.upper()):
        raise NameError_(f"{spec}: no exact backbone match (got {m.get('matchType')} {m.get('rank')})")
    if m.get("status") not in ("ACCEPTED", "DOUBTFUL"):
        accepted = m.get("acceptedUsageKey")
        raise NameError_(f"{spec}: {m.get('status')}; name the accepted taxon (key {accepted})")
    names[spec] = {"key": m["usageKey"], "name": m.get("canonicalName") or name, "rank": m["rank"].lower(),
                   "status": m["status"].lower()}
    return names[spec]
