"""Fixtures for the imaging tests.

The research samples and the EPFL plugin's reference outputs live in the local data vault named by
``LAMINARIO_FIXTURES`` (never in git): ``samples/`` holds the slide files, ``edf-reference/`` the three
reference focal stacks with the plugin's composites and height maps, and the transform dumps. A test that
needs them is skipped with the reason when the folder is absent; continuous integration never has them.

Tests that need libvips are skipped when ``pyvips`` cannot load the library (``LAMINARIO_VIPS_BIN`` names
the Windows build's folder; on Linux the system library is found on its own).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _fixture_root() -> Path | None:
    """``LAMINARIO_FIXTURES`` from the process environment, else from the settings (the local ``.env``)."""
    value = os.environ.get("LAMINARIO_FIXTURES")
    if not value:
        from app.config import Settings

        value = Settings().fixtures
    if not value:
        return None
    path = Path(value)
    return path if path.is_dir() else None


@pytest.fixture(scope="session")
def fixtures() -> Path:
    root = _fixture_root()
    if root is None:
        pytest.skip("LAMINARIO_FIXTURES is not set to the data vault; fixture tests run locally only")
    return root


@pytest.fixture(scope="session")
def samples(fixtures: Path) -> Path:
    folder = fixtures / "samples"
    if not folder.is_dir():
        pytest.skip(f"no samples folder under {fixtures}")
    return folder


@pytest.fixture(scope="session")
def edf_reference(fixtures: Path) -> Path:
    folder = fixtures / "edf-reference"
    if not folder.is_dir():
        pytest.skip(f"no edf-reference folder under {fixtures}")
    return folder


@pytest.fixture(scope="session")
def vips():
    try:
        from app.imaging.library import vips as load

        module = load()
        module.version(0)
    except Exception as exc:  # the library is absent or cannot be loaded on this machine
        pytest.skip(f"libvips is not available: {exc}")
    return module
