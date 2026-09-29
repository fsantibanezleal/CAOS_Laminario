# U7 · Collection tree, anchors, placement and icons · requirements

R-060 to R-062 moved here verbatim from the design document. R-701 to R-707 are this unit's own.

```
R-060  THE collection tree SHALL give every node a rule, an EN and ES name, an EN and ES description and an icon, and every icon SHALL belong to a node or a facet.
       Gate: tests/collections/test_tree.py::test_tree_integrity

R-061  IF two sibling rules overlap without a priority, THEN THE tree check SHALL fail.
       Gate: tests/collections/test_tree.py::test_sibling_overlap_needs_priority

R-062  WHEN an anchor is given, THE placement engine SHALL return the same suggestion every time.
       Gate: tests/collections/test_placement.py::test_deterministic_suggestion

R-701  IF a submission's anchor or host does not resolve (a key outside the GBIF backbone, a name outside its vocabulary, a mineral without a known or declared class), THEN THE API SHALL refuse it, naming the field and what it expected.
       Gate: tests/collections/test_api.py::test_submissions_are_checked_against_the_tree

R-702  IF a slide case is placed at a node that does not accept its anchor, THEN THE API SHALL refuse it and name the suggested node, unless a curator overrides the placement with a reason.
       Gate: tests/collections/test_api.py::test_submissions_are_checked_against_the_tree

R-703  THE IIIF Collection of every node SHALL validate against the pinned IIIF Presentation 3 schema and list the node's children and the manifests placed at it, or shown by it for a host view.
       Gate: tests/collections/test_api.py::test_host_views_and_iiif_collections

R-704  EVERY icon drawing SHALL stay inside the clear area of its frame, use one stroke weight and only the page's colour, and the built sprite SHALL carry the EN and ES titles of its node or facet.
       Gate: tests/collections/test_icons.py::test_icon_gate

R-705  WHEN a taxon key has been resolved once, THE system SHALL place it again from the cached lineage without calling GBIF.
       Gate: tests/collections/test_taxa.py::test_lineage_is_fetched_once_and_cached

R-706  THE mineral vocabulary SHALL be the exact rebuild of its two sources, the IMA list and the Wikidata extract.
       Gate: tests/collections/test_vocab.py::test_minerals_json_matches_its_sources

R-707  EVERY rock term taken from the BGS Rock Classification Scheme SHALL occur in its volume.
       Gate: tests/collections/test_vocab.py::test_rock_terms_occur_in_their_volumes
```
