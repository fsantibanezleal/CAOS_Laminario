"""The committed JSON Schemas equal the ones the models generate."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_exporter():
    spec = importlib.util.spec_from_file_location("export_contracts", ROOT / "scripts" / "export_contracts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_schemas_match_the_models():
    exporter = load_exporter()
    for path, text in exporter.expected_files().items():
        assert path.exists(), f"{path.name} is not committed; run scripts/export_contracts.py"
        assert path.read_text(encoding="utf-8") == text, f"{path.name} is stale; run scripts/export_contracts.py"


def test_schema_declares_expected_text_on_constrained_fields():
    exporter = load_exporter()
    schema = exporter.ingest_schema()
    slide = schema["$defs"]["SlideSpec"]["properties"]
    assert slide["format"]["expected"].startswith("one of:")
    assert "20 to 100" in schema["$defs"]["SizeMm"]["properties"]["w_mm"]["expected"]
    assert exporter.catalog_schema()["properties"].keys() == {"slide", "slidePage", "slideSummary", "validation"}
