"""The base collection (U8): an offline release lane that runs on the development machine, never in the server.

1. **harvest**: source adapters list candidates with their metadata (``sources/``);
2. **curate**: a person chooses slides into the lock, ``data/base/lock.yaml``, with the anchor, the placement and
   the role of every image;
3. **acquire**: every image is downloaded once into the data vault, its SHA-256 and retrieval date recorded in
   ``data/base/acquired.json``;
4. **validate**: every lock entry becomes a slide-case submission and passes the ingestion contract, the tree's
   anchor and placement checks and the base-collection acceptance rules; the report is committed;
5. **bake**: pyramids and derivatives are written into a declared output root with a manifest;
6. **import**: on the server, the manifest is verified and loaded, never re-baked.

Nothing here runs in CI or at deploy (design document, section 3).
"""
