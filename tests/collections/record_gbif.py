"""Record the GBIF answers the tests replay (run by hand when a fixture is added; the tests never go online).

    python tests/collections/record_gbif.py

Writes ``tests/collections/gbif/species-{key}.json``, ``parents-{key}.json`` and ``suggest-{q}.json`` exactly as
GBIF answered them on the day, for the replay server in ``tests/gbif_replay.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx2

API = "https://api.gbif.org/v1"
OUT = Path(__file__).resolve().parent / "gbif"
BACKBONE = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"

#: key: why the tests need it
KEYS = {
    1032608: "Polyplax borealis, the louse of the standard payload",
    2439381: "Thomomys, its host (a pocket gopher)",
    4987991: "Pediculus humanus, a louse family of the lice rule",
    2436436: "Homo sapiens, human tissue under Mammals",
    9326020: "Gallus gallus, a feather under Birds",
    8215487: "Salmo trutta, a ray-finned fish (no class in the backbone)",
    5285637: "Pinus sylvestris, pollen under Pollen and spores, wood under Plants",
    112: "Spirochaetes, a synonym whose accepted taxon is Spirochaetota",
    10707403: "Spirochaetota, the accepted taxon of 112",
    298129616: "Polyplax serrata from another checklist: not a backbone key",
}
SUGGEST = ["Polyplax"]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with httpx2.Client(timeout=30.0, headers={"User-Agent": "Laminario test fixtures"}) as client:
        for key in KEYS:
            record = client.get(f"{API}/species/{key}").json()
            (OUT / f"species-{key}.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                                                     encoding="utf-8", newline="\n")
            if record.get("datasetKey") == BACKBONE:
                parents = client.get(f"{API}/species/{key}/parents").json()
                (OUT / f"parents-{key}.json").write_text(json.dumps(parents, indent=1, ensure_ascii=False) + "\n",
                                                         encoding="utf-8", newline="\n")
        for q in SUGGEST:
            found = client.get(f"{API}/species/suggest", params={"datasetKey": BACKBONE, "limit": 10, "q": q}).json()
            (OUT / f"suggest-{q.lower()}.json").write_text(json.dumps(found, indent=1, ensure_ascii=False) + "\n",
                                                           encoding="utf-8", newline="\n")
    print(f"recorded {len(KEYS)} taxa and {len(SUGGEST)} suggestions in {OUT}")


if __name__ == "__main__":
    main()
