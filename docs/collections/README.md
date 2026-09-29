# Collections

The collection tree is what a visitor browses: three realms, eighteen collections, 130 sub-collections and groups.
Under it every slide is anchored to a real classification. This folder documents the tree as data; the model, the
rule semantics and the placement engine are in the wiki page
[09 The collection tree](../architecture/09_collections.md).

| Page | What |
|---|---|
| [tree.md](tree.md) | every node with its English and Spanish names, its description and its rule, generated from the file the product serves |
| [svg/icons.svg](svg/icons.svg) | the contact sheet of the 186 icons at 48 and 16 pixels, both themes |

## Where the tree and its vocabularies live

| File | What | Built or checked by |
|---|---|---|
| `app/collections/data/tree.yaml` | the tree: nodes, names, descriptions, rules, priorities | the tree guard (`tests/collections/test_tree.py`) |
| `app/collections/data/taxa.lock.json` | GBIF keys and lineages of the 134 taxa the tree names | `scripts/lock_taxa.py` (`--check` for changes) |
| `app/collections/data/vocab/minerals.json` | 6,200 IMA species with Nickel-Strunz codes and crystal systems, 27 group names | `scripts/build_minerals.py` from the data vault |
| `app/collections/data/vocab/mineral_groups.yaml` | group and varietal names, and where each takes its code | read by `build_minerals.py` |
| `app/collections/data/vocab/rocks.yaml` | 365 rock names with their family and source | `scripts/check_rock_terms.py` against the RCS volumes |
| `app/collections/data/vocab/parts.yaml` | parts of organisms (tissues, organs, plant organs) | the tree guard |
| `app/collections/data/vocab/materials.yaml` | material terms and families | the tree guard |
| `app/collections/data/vocab/crystals.yaml` | crystal origins, systems, snow-crystal categories | the tree guard |
| `app/collections/data/vocab/facets.yaml` | preparation and modality names | the facets API |

The sources of the mineral and rock vocabularies are kept in the data vault (`LAMINARIO_FIXTURES/vocab`): the IMA
list of January 2026, the Wikidata extract of 2026-09-29 with its query, and the three BGS RCS volumes; their SHA-256
are recorded in `minerals.json`.

## Licences

| Data | Licence |
|---|---|
| GBIF Backbone Taxonomy (keys, names, lineages) | CC BY 4.0 |
| IMA list of minerals (names, statuses), and so `minerals.json` | CC BY-SA 3.0 |
| Nickel-Strunz codes and crystal systems from Wikidata | CC0 |
| BGS Rock Classification Scheme names | the scheme's terms, cited to their volumes |
| The tree, the Laminario vocabularies and the icons | MIT, with the repository |

## Changing the tree

1. Edit `tree.yaml`. A new taxon is written `Name@rank` exactly as the GBIF backbone has it.
2. Run `python scripts/lock_taxa.py`; it stops at a name that is not an exact, accepted match.
3. Draw the node's icon in `frontend/src/icons/sprite.svg` and run `python scripts/build_icons.py`.
4. Run `python scripts/render_tree_docs.py` and the tests in `tests/collections`: the guard names every node without
   a name, description, icon or resolvable rule, every unreachable node, and every pair of siblings that could take
   the same slide with the same priority.
