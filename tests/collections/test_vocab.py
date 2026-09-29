"""Anchor vocabularies: every kind resolves to its canonical form and path, or says what it expected."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

from app.collections import vocab
from app.collections.vocab import Problem, Term, resolve_term, strunz_path

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def vault() -> Path:
    fixtures = os.environ.get("LAMINARIO_FIXTURES")
    if not fixtures or not (Path(fixtures) / "vocab" / "ima-list-2026-01.pdf").exists():
        pytest.skip("the vocabulary sources are in the data vault (LAMINARIO_FIXTURES/vocab)")
    return Path(fixtures)


def test_strunz_paths():
    assert strunz_path("9.AF.15") == "9.A.F.15"
    assert strunz_path("9.FA") == "9.F.A"
    assert strunz_path("02.BA.") == "2.B.A"
    assert strunz_path("10") == "10"
    assert strunz_path("9.G") == "9.G"
    assert strunz_path("11") is None
    assert strunz_path("silicate") is None


def test_minerals():
    v = vocab.load()
    assert v.mineral_about["counts"]["species"] == 6200, "the count the IMA list itself states"
    assert resolve_term("mineral", "quartz") == Term("Quartz", "species", "4.D.A.05", "4.DA.05")
    assert resolve_term("mineral", "Olivine") == Term("Olivine", "group", "9.A.C.05", "9.AC.05")
    assert resolve_term("mineral", "barite").ref == "Baryte"
    assert resolve_term("mineral", "Gold").path == "1.A.A.05"
    missing = resolve_term("mineral", "Abellaite")
    assert isinstance(missing, Problem) and missing.field == "specimen.anchor.classification"
    assert resolve_term("mineral", "Abellaite", "5") == Term("Abellaite", "species", "5", "5")
    assert resolve_term("mineral", "Quartz", "4.D") == Term("Quartz", "species", "4.D.A.05", "4.DA.05")
    wrong = resolve_term("mineral", "Quartz", "9")
    assert isinstance(wrong, Problem) and "4.DA.05" in wrong.message
    unknown = resolve_term("mineral", "kryptonite")
    assert isinstance(unknown, Problem) and unknown.field == "specimen.anchor.ref"
    assert "olivine" in unknown.expected


def test_rocks():
    assert resolve_term("rock", "Granite") == Term("granite", None, "igneous.coarse")
    assert resolve_term("rock", "alkali feldspar granite").ref == "alkali-feldspar-granite"
    assert resolve_term("rock", "travertine") == Term("limestone", None, "sedimentary.carbonate")
    assert resolve_term("rock", "lamprophyre").path == "igneous.exotic"
    assert resolve_term("rock", "pallasite").path == "meteorite"
    assert isinstance(resolve_term("rock", "breccia"), Problem), "the scheme leaves breccia out on purpose"
    assert isinstance(resolve_term("rock", "granite", "9"), Problem)
    assert len(vocab.load().rocks) == 365


def test_crystals_and_materials():
    assert resolve_term("crystal", "ice/hexagonal", "p") == Term("ice/hexagonal", None, "ice.P", "P")
    assert resolve_term("crystal", "liquid") == Term("liquid", None, "liquid")
    assert isinstance(resolve_term("crystal", "ice/pentagonal"), Problem)
    assert isinstance(resolve_term("crystal", "chemical", "P"), Problem)
    assert isinstance(resolve_term("crystal", "ice", "Z"), Problem)
    assert isinstance(resolve_term("crystal", "plasma"), Problem)
    assert resolve_term("material", "Potato starch") == Term("potato-starch", None, "food")
    assert isinstance(resolve_term("material", "unobtainium"), Problem)


def test_parts_and_search():
    assert vocab.check_part("feather") is None
    assert vocab.check_part("wing-of-bat").field == "specimen.part"
    assert [i["ref"] for i in vocab.search("mineral", "olivi", 3)][0] == "Olivine"
    assert vocab.search("rock", "granod")[0]["ref"] == "granodiorite"
    assert vocab.search("material", "micro")[0]["ref"].startswith("microplastic")
    assert vocab.search("taxon", "Aves") == []


def test_minerals_json_matches_its_sources():
    builder = load_script("build_minerals")
    data = builder.build(vault())
    committed = (ROOT / "app" / "collections" / "data" / "vocab" / "minerals.json").read_text(encoding="utf-8")
    assert builder.json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace('],["', '],\n["') + "\n" \
        == committed


def test_rock_terms_occur_in_their_volumes():
    assert load_script("check_rock_terms").missing_terms(vault()) == []
