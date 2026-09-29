"""R-1202: every validation error and flag of a slide case carries a stable code and its parameters, and the
interface has a message for every code in English and Spanish."""

from __future__ import annotations

import copy
import re
from pathlib import Path

from app.contracts.ingest import validate_submission
from tests import payloads

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ["app/contracts/ingest.py", "app/collections/vocab.py", "app/collections/service.py"]
#: Pydantic's error types a slide case meets, which the interface words itself.
TYPES = ["missing", "extra_forbidden", "string_pattern_mismatch", "string_too_long", "string_too_short",
         "greater_than_equal", "less_than_equal", "greater_than", "less_than", "literal_error", "float_parsing",
         "int_parsing", "date_from_datetime_parsing", "url_parsing", "too_short", "too_long", "value_error"]


def codes_in_sources() -> set[str]:
    found: set[str] = set()
    for name in SOURCES:
        text = (ROOT / name).read_text(encoding="utf-8")
        found |= set(re.findall(r'code="([a-z_]+)"', text))
        found |= set(re.findall(r'Flag\("([a-z_]+)"', text))
    return found


def catalogue_keys(lang: str) -> set[str]:
    text = (ROOT / "frontend" / "src" / "i18n" / f"{lang}.ts").read_text(encoding="utf-8")
    return set(re.findall(r'^\s*"(validation\.[a-z_.]+)"\s*:', text, re.M))


def test_every_code_has_its_message_in_both_languages():
    codes = codes_in_sources()
    assert len(codes) >= 40, sorted(codes)
    wanted = {f"validation.{c}" for c in codes} | {f"validation.type.{t}" for t in TYPES} | {"validation.unknown"}
    for lang in ("en", "es"):
        missing = wanted - catalogue_keys(lang)
        assert not missing, f"{lang}: {sorted(missing)}"


def test_refusals_carry_their_code_and_parameters():
    payload = copy.deepcopy(payloads.contribution())
    payload["slide"]["coverslip"] = "24x60"
    payload["slide"]["format"] = "petro_27x46"
    payload["assets"][1]["licence"] = "https://creativecommons.org/licenses/by-nd/4.0/"
    report = validate_submission(payload)
    by_code = {e["code"]: e for e in report.errors}
    assert by_code["coverslip_too_large"]["params"] == {"width": "46", "height": "27"}
    assert by_code["licence_refused"]["params"]["origin"] == "contribution"

    broken = copy.deepcopy(payloads.contribution())
    del broken["slide"]["preparation"]
    broken["slide"]["catalogue_number"] = "x" * 500
    errors = {e["field"]: e for e in validate_submission(broken).errors}
    assert errors["slide.preparation"]["code"] == "type.missing"
    assert errors["slide.catalogue_number"]["code"] == "type.string_too_long"
    assert errors["slide.catalogue_number"]["params"]["max_length"].isdigit()
    assert all(e["code"] for e in validate_submission(broken).errors)


def test_flags_carry_their_parameters():
    payload = copy.deepcopy(payloads.contribution())
    payload["assets"][0]["exif"]["datetime_original"] = "2019-05-20T10:00:00"
    flags = {f["code"]: f for f in validate_submission(payload).flags}
    assert flags["exif_date_mismatch"]["params"] == {"shot": "2019-05-20", "collected": "2019-04-20"}
