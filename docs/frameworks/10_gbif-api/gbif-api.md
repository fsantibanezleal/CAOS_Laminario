# The GBIF species API and the GBIF Backbone Taxonomy

## What and why

GBIF, the Global Biodiversity Information Facility, publishes the GBIF Backbone Taxonomy (checklist dataset
`d7dddbf4-2cf0-4f39-9b2a-bb099caae36c`, CC BY 4.0), the classification its occurrence records are organised by, and
a free JSON API over it. Laminario anchors every organism slide to a backbone usage key (dossier 03), because the
keys are stable, the classification covers every kingdom the tree needs, and a key links the slide to GBIF's own
page and records.

## Use (exact, verified 2026-09-29)

| Call | Laminario uses it for |
|---|---|
| `GET /v1/species/match?name=&rank=&strict=true` | locking the tree's taxa (`scripts/lock_taxa.py`): an EXACT match at the rank, ACCEPTED (or DOUBTFUL, noted) |
| `GET /v1/species/{key}` | a slide's taxon: name, rank, status, `acceptedKey` of a synonym, `datasetKey` (must be the backbone) |
| `GET /v1/species/{key}/parents` | the lineage, kingdom first, that placement needs |
| `GET /v1/species/suggest?datasetKey=&q=&limit=` | the anchor field's suggestions (it also matches epithets: `Polyplax` suggests the starfish *Allostichaster polyplax*) |

No key is needed; requests carry a `User-Agent` naming Laminario. The base URL is `LAMINARIO_GBIF_API_URL`
(default `https://api.gbif.org/v1`).

## Applying it here

- `app/collections/taxa.py` reads a key once and stores it in the `taxon` table; placement then works offline
  (R-705). When GBIF does not answer, the API returns 503 and the submission can be retried.
- `app/collections/data/taxa.lock.json` holds the keys and lineages of the 134 taxa the tree names; `lock_taxa.py
  --check` reports any change since the lock.
- The tests never call GBIF: `tests/collections/record_gbif.py` recorded real answers and `tests/gbif_replay.py`
  serves them on a local port for every test run.

## Caveats and licence

- The backbone is not always the textbook, and the tree follows it (dossier 09): no Phthiraptera (lice are its 26
  families inside Psocodea), no Actinopterygii (ray-finned fish orders sit under Chordata), no Reptilia (four
  classes), Equisetum inside Polypodiopsida, Radiozoa a synonym of the kingdom Chromista, older bacterial phylum
  names (Firmicutes, Actinobacteriota, Proteobacteria).
- `species/match` without a rank can meet a homonym: for "Bacteria" it answers NONE with "Multiple equal matches",
  the kingdom and the stick-insect genus *Bacteria* Berthold, 1827; with `rank=KINGDOM` it finds the kingdom.
- When GBIF republishes the backbone, keys and lineages can change; `lock_taxa.py --check` reports every difference
  from the lock, and slides keep the cached lineage they were placed with.
- Data: CC BY 4.0 (the backbone). The API itself has no licence terms beyond GBIF's data use agreement.
