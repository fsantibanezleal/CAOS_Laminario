# U1 · Data model and contracts · requirements

R-005 to R-007 moved here verbatim from the design document. R-101 to R-106 are this unit's own.

Rules enforced by later units are listed where they belong: anchor resolution and placement acceptance by the
collection tree (U7), file-level rules (readable header, dimensions, decompression bomb, planes of one stack sharing
dimensions) by the imaging engine (U2) and the upload verifier (U5).

```
R-005  WHEN a submission violates any rejecting rule of the ingestion contract, THE API SHALL reject it with HTTP 422 naming the field and the expected range.
       Gate: tests/contracts/test_ingest_contract.py::test_every_rejecting_rule_names_field_and_range

R-006  WHEN a submission carries a flagging condition of the ingestion contract, THE API SHALL accept it and return the flags.
       Gate: tests/contracts/test_ingest_contract.py::test_flagging_rules_accept_and_report

R-007  THE generated TypeScript catalog types SHALL equal the types generated from the current catalog JSON Schema.
       Gate: frontend/scripts/check-contract-drift.mjs

R-101  THE committed JSON Schemas of the ingestion and catalog contracts SHALL equal the schemas generated from the current models.
       Gate: tests/contracts/test_schema_export.py::test_committed_schemas_match_the_models

R-102  THE licence policy SHALL accept for the base collection only CC0, the public domain mark, the no-known-copyright statement, CC BY and CC BY-SA, and for contributions also CC BY-NC and CC BY-NC-SA, and SHALL normalise equivalent URIs to one canonical form.
       Gate: tests/contracts/test_licence_policy.py::test_policy_sets_and_normalisation

R-103  WHEN a slide is created, THE system SHALL assign an 8-character Crockford base-32 short id that is unique, and SHALL resolve a short id regardless of letter case and of the letters Crockford treats as digits.
       Gate: tests/db/test_short_id.py::test_short_ids_are_unique_and_resolve_case_insensitively

R-104  THE catalog record SHALL never carry the exact coordinates of a specimen whose geoprivacy is obscured or private, and an obscured point SHALL stay inside its 0.2 degree cell and be the same on every request.
       Gate: tests/contracts/test_catalog_privacy.py::test_obscured_and_private_coordinates_never_leave

R-105  WHEN the database is upgraded from empty to the head migration, THE schema SHALL contain exactly the tables and columns the models declare.
       Gate: tests/db/test_migrations.py::test_head_matches_models

R-106  WHILE the API and the worker share the database, THE database SHALL run in write-ahead-log mode with a busy timeout and enforced foreign keys.
       Gate: tests/db/test_migrations.py::test_sqlite_pragmas_on_every_connection
```
