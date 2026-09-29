"""Source adapters: each lists candidates from one open source, with everything the lock and the provenance need.

A candidate is a plain dict (written as one JSON line):

- ``source``: the adapter (``commons``, ``nhm``, ``smithsonian``, ``zenodo``, ``openslide``);
- ``record_id``, ``record_url``: the source's own record, as it names it;
- ``title``, ``description``: text for the person curating;
- ``media``: the images, each with ``media_id``, ``url`` (the bytes to acquire), ``thumb`` (for review), ``width``,
  ``height``, ``mime``, ``licence`` (canonical URI), ``creator`` and ``rights_holder``;
- ``hints``: what the source says about the subject (a GBIF key, a scientific name, categories).

Only candidates whose every image carries a licence of the base policy are kept; the rest are counted, not listed.
"""
