"""The data-contract reference pages are generated from the committed schemas and equal them."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load():
    spec = importlib.util.spec_from_file_location("render_contract_docs", ROOT / "scripts" / "render_contract_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_contract_pages_match_the_schemas():
    renderer = load()
    for path, text in renderer.expected_files().items():
        assert path.read_text(encoding="utf-8") == text, f"{path.name} is stale: run scripts/render_contract_docs.py"


def test_every_model_has_a_table():
    renderer = load()
    pages = renderer.expected_files()
    slide_case = pages[renderer.OUT / "01_slide-case.md"]
    for model in ("SlideCaseSubmission", "SlideSpec", "SpecimenSpec", "AssetSpec", "PlaneSpec", "SourceSpec"):
        assert f"### {model}\n" in slide_case
    catalog = pages[renderer.OUT / "02_catalog-records.md"]
    for model in ("SlideRecord", "AssetRecord", "MediaRecord", "JobRecord", "JobEventRecord"):
        assert f"### {model}\n" in catalog
