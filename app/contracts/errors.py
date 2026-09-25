"""Turn a Pydantic validation error into the contract's error list: field, message, expected range.

Every constrained field declares what it expects in its JSON Schema extra (``expected``), and every
cross-field rule raises a ``PydanticCustomError`` whose context carries ``expected``. The formatter uses
the declaration first, the error context second, and a description of the error type last, so no error
reaches a client without saying what would have been accepted.
"""

from __future__ import annotations

import typing
from typing import Any

from pydantic import BaseModel, ValidationError

#: Descriptions for built-in error types that carry no range of their own.
_TYPE_EXPECTATIONS = {
    "missing": "a value",
    "extra_forbidden": "no such field",
    "float_parsing": "a number",
    "float_type": "a number",
    "int_parsing": "a whole number",
    "int_type": "a whole number",
    "bool_parsing": "true or false",
    "string_type": "text",
    "list_type": "a list",
    "model_type": "an object",
    "dict_type": "an object",
    "url_parsing": "an absolute URL",
    "url_scheme": "an http or https URL",
    "date_from_datetime_parsing": "a date YYYY-MM-DD",
    "date_parsing": "a date YYYY-MM-DD",
    "date_type": "a date YYYY-MM-DD",
}


def _field_expectation(model: type[BaseModel] | None, loc: tuple[Any, ...]) -> str | None:
    """Walk ``loc`` through nested models and return the ``expected`` declared on the final field."""
    current: Any = model
    declared: str | None = None
    for part in loc:
        if isinstance(part, int):
            continue
        if not (isinstance(current, type) and issubclass(current, BaseModel)):
            return declared
        field = current.model_fields.get(part)
        if field is None:
            return declared
        extra = field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}
        declared = extra.get("expected")
        current = _inner_model(field.annotation)
    return declared


def _inner_model(annotation: Any) -> Any:
    """The model class inside an annotation such as ``list[Model]`` or ``Model | None``."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for arg in typing.get_args(annotation):
        found = _inner_model(arg)
        if found is not None:
            return found
    return None


def _describe(err: dict[str, Any]) -> str:
    ctx = err.get("ctx") or {}
    if "expected" in ctx:
        return str(ctx["expected"])
    kind = err.get("type", "")
    if kind == "greater_than_equal":
        return f"at least {ctx.get('ge')}"
    if kind == "less_than_equal":
        return f"at most {ctx.get('le')}"
    if kind == "greater_than":
        return f"more than {ctx.get('gt')}"
    if kind == "less_than":
        return f"less than {ctx.get('lt')}"
    if kind == "string_too_long":
        return f"at most {ctx.get('max_length')} characters"
    if kind == "string_too_short":
        return f"at least {ctx.get('min_length')} characters"
    if kind == "too_short":
        return f"at least {ctx.get('min_length')} items"
    if kind == "too_long":
        return f"at most {ctx.get('max_length')} items"
    if kind == "string_pattern_mismatch":
        return f"text matching {ctx.get('pattern')}"
    return _TYPE_EXPECTATIONS.get(kind, "a valid value")


def contract_errors(exc: ValidationError, model: type[BaseModel] | None = None) -> list[dict[str, str]]:
    """The contract's error list for a validation error of ``model``."""
    out: list[dict[str, str]] = []
    for err in exc.errors(include_url=False):
        loc = tuple(err.get("loc", ()))
        # FastAPI prefixes body errors with "body"; the contract's fields start after it.
        if loc and loc[0] == "body":
            loc = loc[1:]
        field = ".".join(str(p) for p in loc) or "(submission)"
        ctx = err.get("ctx") or {}
        expected = ctx.get("expected") or _field_expectation(model, loc) or _describe(err)
        out.append({"field": field, "message": err.get("msg", "invalid"), "expected": str(expected)})
    return out
