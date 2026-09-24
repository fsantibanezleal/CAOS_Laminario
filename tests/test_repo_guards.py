"""The repository guards, each checked against positive and negative controls.

A guard that passes everything proves nothing, so every rule is shown to fire on the case it exists for.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hygiene = load("check_repo_hygiene")
residue = load("check_template_residue")
sdd = load("check_sdd")


def test_hygiene_flags_every_forbidden_kind_of_path():
    flagged = {
        ".env": "a real .env",
        "app/.env.production": "a real .env",
        ".venv/Lib/site.py": "virtual environment",
        "vendor/vips.dll": "native binary",
        "data/cells.npy": "heavy data",
        "fixtures/CMU-1.svs": "slide or pyramid",
        "store/slide.ndpi": "slide or pyramid",
        "store/pyramid.tif": "slide or pyramid",
        "laminario.sqlite3": "database file",
        "laminario.db-wal": "database file",
    }
    for path, reason in flagged.items():
        problems = hygiene.path_problems(path)
        assert any(reason in p for p in problems), (path, problems)


def test_hygiene_allows_the_files_a_repository_needs():
    for path in [".env.example", "app/main.py", "docs/architecture/svg/overview.svg", "README.md",
                 "frontend/src/icons/sprite.svg", "requirements.txt"]:
        assert hygiene.path_problems(path) == [], path


def test_hygiene_flags_leaked_local_paths_and_not_ordinary_text():
    leaked = "cd " + "D:" + "\\_Repos\\x"
    assert hygiene.content_problems("README.md", leaked)
    assert hygiene.content_problems("README.md", "the E: drive holds " + "E:" + "\\_Datos")
    assert hygiene.content_problems("README.md", "see /srv/laminario and C:/tmp") == []


def test_hygiene_passes_on_this_repository():
    assert hygiene.check(ROOT) == []


def test_residue_guard_forbids_a_pages_workflow():
    assert ".github/workflows/deploy-pages.yml" in residue.FORBIDDEN_PATH_SUBSTR


def test_sdd_guard_rejects_a_requirement_whose_gate_does_not_exist(tmp_path):
    design = tmp_path / "docs" / "design"
    design.mkdir(parents=True)
    (design / "SDD.md").write_text(
        "```\nR-001  THE system SHALL do a thing.\n       Gate: tests/test_missing.py::test_nothing\n```\n",
        encoding="utf-8",
    )
    problems = sdd.check_document(tmp_path, Path("docs/design/SDD.md"))
    assert any("does not exist" in p for p in problems)


def test_sdd_guard_passes_on_this_repository():
    assert sdd.main(["check_sdd.py", str(ROOT)]) == 0
