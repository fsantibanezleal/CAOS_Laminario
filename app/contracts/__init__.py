"""The two contracts of the product.

- ``ingest``: what a slide-case submission must satisfy before anything is stored.
- ``catalog``: the record the web reads for a slide and its assets.

Both are Pydantic models whose JSON Schemas are committed in ``contracts/`` and mirrored in TypeScript.
"""
