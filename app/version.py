"""The product version, read once from the ``VERSION`` file (the single source of truth).

``VERSION`` holds the padded display form ``X.XX.XXX``; ``semver()`` gives the form manifests need.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def semver(display: str = VERSION) -> str:
    """Return the semantic-version form of a display version: ``0.12.003`` becomes ``0.12.3``."""
    major, minor, patch = (int(part) for part in display.split("."))
    return f"{major}.{minor}.{patch}"
