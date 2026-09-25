#!/usr/bin/env python3
"""Write the JSON Schemas of both contracts to ``contracts/``.

``contracts/ingest.schema.json``: the slide-case submission (validation mode).
``contracts/catalog.schema.json``: the records the web reads (serialization mode), rooted in one object whose
properties name each top-level record, so a TypeScript generator emits every interface.

A test fails when the committed files differ from what this script would write; the frontend generates its
TypeScript types from the committed files and a second check fails when those drift.

Usage: ``python scripts/export_contracts.py`` (writes) or ``--check`` (exit 1 on any difference).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic.json_schema import models_json_schema

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.contracts import catalog as c  # noqa: E402
from app.contracts.ingest import SlideCaseSubmission  # noqa: E402

OUT = ROOT / "contracts"
CATALOG_ROOTS = {
    "slide": c.SlideRecord,
    "slidePage": c.SlidePage,
    "slideSummary": c.SlideSummary,
    "validation": c.ValidationResult,
}


def ingest_schema() -> dict:
    schema = SlideCaseSubmission.model_json_schema(mode="validation")
    schema["$id"] = "https://laminario.ml.fasl-work.com/contracts/ingest.schema.json"
    return schema


def catalog_schema() -> dict:
    refs, defs = models_json_schema(
        [(m, "serialization") for m in CATALOG_ROOTS.values()], ref_template="#/$defs/{model}"
    )
    properties = {name: refs[(model, "serialization")] for name, model in CATALOG_ROOTS.items()}
    return {
        "$id": "https://laminario.ml.fasl-work.com/contracts/catalog.schema.json",
        "title": "LaminarioCatalog",
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
        "$defs": defs["$defs"],
    }


def strip_property_titles(node):
    """Drop the ``title`` Pydantic puts on every property; a TypeScript generator would name a type after each.

    Model titles (under ``$defs``) stay: they become the interface names.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                for field_schema in value.values():
                    if isinstance(field_schema, dict):
                        field_schema.pop("title", None)
                        strip_property_titles(field_schema)
            else:
                strip_property_titles(value)
    elif isinstance(node, list):
        for item in node:
            strip_property_titles(item)
    return node


def render(schema: dict) -> str:
    return json.dumps(strip_property_titles(schema), indent=2, ensure_ascii=False) + "\n"


def expected_files() -> dict[Path, str]:
    return {
        OUT / "ingest.schema.json": render(ingest_schema()),
        OUT / "catalog.schema.json": render(catalog_schema()),
    }


def main(argv: list[str]) -> int:
    files = expected_files()
    if "--check" in argv:
        stale = [p.name for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            print("contract schemas out of date: " + ", ".join(stale) + " (run scripts/export_contracts.py)")
            return 1
        print("contract schemas: OK")
        return 0
    OUT.mkdir(exist_ok=True)
    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
