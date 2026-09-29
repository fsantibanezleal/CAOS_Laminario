# U7 · Collection tree, anchors, placement and icons · design

The model, with its diagram and the formal rule semantics, is in the wiki page
[09 The collection tree](../../../architecture/09_collections.md); the tree itself, node by node, is in
[docs/collections](../../../collections/README.md). The research is dossiers 03 and 09 of the planning record. This
page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| The tree: 191 nodes (3 realms, 18 collections, 130 sub-collections and groups with the shared organ systems counted once), names and descriptions in EN and ES | `app/collections/data/tree.yaml` |
| The GBIF keys and lineages of the 134 taxa the tree names | `app/collections/data/taxa.lock.json`, `scripts/lock_taxa.py` |
| Vocabularies: minerals (6,200 IMA species, 27 group names), rocks (365 terms), parts, materials, crystal origins and snow-crystal categories, facets | `app/collections/data/vocab/`, `scripts/build_minerals.py`, `scripts/check_rock_terms.py` |
| Rules, the tree guard and placement | `app/collections/{rules,tree,placement}.py` |
| The GBIF taxon cache (table `taxon`, migration 0006) | `app/collections/taxa.py` |
| The submission check (anchor, part, host, placement) | `app/collections/service.py`, used by `POST /api/slide-cases` and `/validate` |
| The API and the IIIF Collection per node | `app/routers/collections.py`, `app/services/collections.py` |
| The contract fields `specimen.part`, `specimen.preservation`, `anchor.classification`; the collection records | `app/contracts/{ingest,catalog}.py` |
| 186 icons, their build and gate, the contact sheet | `frontend/src/icons/sprite.svg`, `scripts/build_icons.py`, `frontend/public/icons.svg`, `docs/collections/svg/icons.svg` |

## Decisions

- **A curation layer over real classifications** (dossier 03). A slide is anchored to a taxon, a rock, a mineral,
  a crystal or a material; the tree is what a visitor browses, and each node's rule says which anchors it takes.
- **The tree is data**, one YAML file with the rules next to the names, so the guard, the API, the docs and the
  icon build read the same thing. The ten vertebrate organ systems are written once and shared by the five
  vertebrate collections (the dossier counts them, and their icons, once).
- **Rules are conjunctions over five dimensions**: anchor kind, taxa (with exclusions), vocabulary path prefixes,
  part and preservation, with alternatives (`any`) and a priority. A node without anchor conditions is a container
  that accepts what its children accept. Relation nodes (Parasites and hosts) are views: nothing is placed in them.
- **A taxon that contains an excluded clade is not taken.** "Insects other than beetles" does not take the class
  Insecta, which would also claim the beetles; an anchor at class level therefore stays with Insects, and one at
  kingdom level with its realm. Found while building: the first version put the kingdom Animalia in Other
  invertebrates.
- **The realms have explicit rules** (Life: recent taxa and pollen samples; Earth: fossil taxa, rocks, minerals;
  Matter: crystals and made materials), so a broad anchor always has a place, and overlaps between realms are
  checked like any others.
- **Placement is a walk down by priority**; the guard refuses siblings that could take the same slide with the same
  priority (R-061), so the walk never meets a tie and does not depend on the order of siblings (R-062, checked on
  the tree with every list of siblings reversed). The accepting nodes (the node and all its ancestors accept) are
  where a contributor may place a slide; anywhere else needs a curator's reason (R-702).
- **The overlap test is symbolic**: two clauses overlap when every dimension admits a common value; for taxa, when
  one clause's clade contains the other's and the deeper one is not excluded. It can only err toward asking for a
  priority. The guard also proves every node reachable, by placing hypothetical specimens built from its rule.
- **The GBIF backbone decides the taxon rules**, as it is, verified name by name (`scripts/lock_taxa.py` refuses a
  name that is not an exact, accepted match at its rank): it has no Phthiraptera (lice are its 26 families inside
  Psocodea), no Actinopterygii (ray-finned fish orders sit directly under Chordata, so Fishes is the chordates less
  the tetrapods, tunicates and lancelets), no Reptilia (four classes: Squamata, Testudines, Crocodylia,
  Sphenodontia), Equisetum inside Polypodiopsida, Radiozoa as a synonym (radiolarians are Polycystina, DOUBTFUL, and
  Acantharia), Naegleria inside Amoebozoa, and the older bacterial phylum names (Firmicutes, Actinobacteriota,
  Proteobacteria).
- **Taxon lineages are cached** in `taxon` on first use (the record and `/parents`), so placement works offline
  afterwards (R-705); a synonym is followed to its accepted taxon; a key from another checklist is refused. When
  GBIF does not answer, the API says so with 503 instead of guessing.
- **Minerals**: the IMA list (6,200 species, the count the list states, CC BY-SA 3.0) joined with Nickel-Strunz
  codes from Wikidata (CC0, 4,808 of the species); group and varietal names in common use (olivine, biotite,
  plagioclase) take their code from Wikidata or from a named member species. A species without a code needs the
  class declared (`anchor.classification`); a declared class that contradicts the table is refused. The file is
  rebuilt from the vault by a script and must match (R-706).
- **Rocks**: the three BGS RCS volumes. The igneous appendix gives each name its group; the fourth igneous group is
  the scheme's own "exotic crystalline rocks" (lamprophyres, carbonatites, kimberlites, lamproites, melilitic,
  kalsilitic and leucitic rocks), so the tree has 130 sub-collections and groups instead of the 129 of dossier 03,
  and 186 icons instead of 185. Metamorphic names are grouped as foliated or not only where the scheme defines them
  by fabric. Every scheme term is found in its volume (R-707). Meteorite classes follow Weisberg et al. (2006); ore
  textures and soil are Laminario terms.
- **Crystals** take origin and system (`ice/hexagonal`) and, for ice, the Kikuchi et al. (2013) general category;
  **materials** are a controlled vocabulary; **parts** name tissues and plant organs.
- **The contract** gains `specimen.part`, `specimen.preservation` (recent, fossil, in amber or copal) and
  `anchor.classification`, with cross-field rules (a part only for organisms, preservation only for organisms, a
  classification only for minerals and crystals). The stored anchor is the canonical form (`Quartz`, `granite`).
- **Icons** (dossier 03, section 5): hand-drawn in one sprite; the build adds the stroke, the frame by kind and the
  titles, so these are the same by construction; the gate measures every drawing against its frame (R-704).

## Interfaces used by later units

- U8 (base collection): each lock entry goes through `check_submission`; the coverage matrix counts
  `/api/collections` nodes.
- U9 and U10 (design system, Explore): the sprite at `/icons.svg`, each node's `icon`, the tree with counts, the
  facets, the node pages, `GET /api/slides?node=` (views included).
- U11 (slide page): the placement path for the breadcrumb, the anchor's classification, part and preservation.
- U12 (contribute): `GET /api/anchors/search`, `POST /api/placement` for the live suggestion and the accepting
  nodes, the 503 when GBIF is down.
- U13 (identify): a community identification changes the anchor; placement is recomputed with the same engine.
