#!/usr/bin/env python3
"""Render the field-level data-contract reference from the committed JSON Schemas.

``contracts/ingest.schema.json`` becomes ``docs/data-contract/01_slide-case.md`` and
``contracts/catalog.schema.json`` becomes ``docs/data-contract/02_catalog-records.md``: one table per model, in the
order the models are first referenced, with each field's type, whether it is required, what is accepted (the
contract's own "expected" text, or the enum, range or pattern) and its default. The pages are generated, so they
cannot drift from the models; ``--check`` fails when a committed page differs from what this script writes.

Usage: ``python scripts/render_contract_docs.py`` (writes) or ``--check``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data-contract"
PAGES = {
    "01_slide-case.md": ("ingest.schema.json", "The slide case (ingestion contract)",
                         "What a submission must satisfy before anything is stored. `POST /api/slide-cases/validate` "
                         "runs it without storing. Rules that span several fields, and the conditions that are "
                         "accepted but flagged, are listed in [the data-contract overview](../data-contract.md)."),
    "02_catalog-records.md": ("catalog.schema.json", "Catalog records (what the web reads)",
                              "The records the API returns: slides, pages of slides, summaries, validation "
                              "results and processing jobs. Geoprivacy is already applied to every place."),
}


def _ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def type_text(node: dict) -> str:
    if "$ref" in node:
        name = _ref_name(node["$ref"])
        return f"[{name}](#{name.lower()})"
    if "anyOf" in node:
        parts = [type_text(option) for option in node["anyOf"]]
        return " or ".join(p for p in parts if p != "null") + (" or null" if "null" in parts else "")
    if "enum" in node:
        return "string (enumerated)" if node.get("type") == "string" else "enumerated"
    kind = node.get("type")
    if kind == "array":
        return f"list of {type_text(node.get('items', {}))}"
    if isinstance(kind, list):
        return " or ".join(kind)
    if kind == "string" and node.get("format"):
        return f"string ({node['format']})"
    if kind == "object" and "additionalProperties" in node and isinstance(node["additionalProperties"], dict):
        return f"map of {type_text(node['additionalProperties'])}"
    return kind or "any"


def accepted_text(node: dict) -> str:
    if node.get("expected"):
        return node["expected"]
    options = node.get("anyOf", [node])
    for option in options:
        if "enum" in option:
            return "one of: " + ", ".join(f"`{v}`" for v in option["enum"])
        if "const" in option:
            return f"`{option['const']}`"
    pieces = []
    for key, label in (("minimum", ">="), ("exclusiveMinimum", ">"), ("maximum", "<="), ("exclusiveMaximum", "<"),
                       ("minLength", "length >="), ("maxLength", "length <="), ("minItems", "items >="),
                       ("maxItems", "items <=")):
        for option in options:
            if key in option:
                pieces.append(f"{label} {option[key]}")
    for option in options:
        if "pattern" in option:
            pieces.append(f"pattern `{option['pattern']}`")
    return ", ".join(pieces)


def default_text(node: dict) -> str:
    if "default" not in node:
        return ""
    value = node["default"]
    return "null" if value is None else f"`{json.dumps(value)}`"


def references(node, found: list[str]) -> None:
    if isinstance(node, dict):
        if "$ref" in node:
            name = _ref_name(node["$ref"])
            if name not in found:
                found.append(name)
        for value in node.values():
            references(value, found)
    elif isinstance(node, list):
        for value in node:
            references(value, found)


def model_table(name: str, model: dict) -> list[str]:
    lines = [f"### {name}", ""]
    if model.get("description"):
        lines += [" ".join(model["description"].split()), ""]
    required = set(model.get("required", []))
    lines += ["| Field | Type | Required | Accepted | Default |", "|---|---|---|---|---|"]
    for field, node in model.get("properties", {}).items():
        accepted = accepted_text(node).replace("|", "\\|")
        lines.append(f"| `{field}` | {type_text(node)} | {'yes' if field in required else 'no'} | {accepted} | "
                     f"{default_text(node)} |")
    return lines + [""]


def render(schema_file: str, title: str, intro: str) -> str:
    schema = json.loads((ROOT / "contracts" / schema_file).read_text(encoding="utf-8"))
    definitions = schema.get("$defs", {})
    order: list[str] = []
    references(schema.get("properties", {}), order)
    index = 0
    while index < len(order):
        references(definitions.get(order[index], {}), order)
        index += 1
    order += sorted(set(definitions) - set(order))
    lines = [
        f"# {title}",
        "",
        f"<!-- Generated from contracts/{schema_file} by scripts/render_contract_docs.py; do not edit by hand. -->",
        "",
        intro,
        "",
        f"Schema: [`contracts/{schema_file}`](../../contracts/{schema_file}) (JSON Schema, "
        f"`{schema.get('$id', '')}`).",
        "",
    ]
    if schema.get("title") and schema.get("properties"):
        lines += model_table(schema["title"], schema)
    for name in order:
        lines += model_table(name, definitions[name])
    return "\n".join(lines).rstrip() + "\n"


def expected_files() -> dict[Path, str]:
    return {OUT / page: render(schema, title, intro) for page, (schema, title, intro) in PAGES.items()}


def main(argv: list[str]) -> int:
    files = expected_files()
    if "--check" in argv:
        stale = [p.name for p, text in files.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            print("data-contract pages out of date: " + ", ".join(stale) + " (run scripts/render_contract_docs.py)")
            return 1
        print("data-contract pages: OK")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for path, text in files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
