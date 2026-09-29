"""The collection tree (U7): vocabularies for anchors, the tree and its rules, placement, and the taxon cache.

- ``vocab``: the non-taxon anchor vocabularies (rocks, minerals, crystals, materials), the part vocabulary and the
  facets, loaded from ``data/vocab``.
- ``tree``: the tree of ``data/tree.yaml`` with each node's rule compiled against the taxa lock.
- ``rules``: what a rule accepts, and whether two rules can accept the same slide (the tree guard).
- ``placement``: the suggestion for a slide and the nodes that accept it.
- ``taxa``: the GBIF lineage of a taxon anchor, cached in the database.
"""
