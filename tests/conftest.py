"""Test configuration.

Tests write only inside a temporary directory, never into the repository's data or the canonical
outputs. The base temporary directory is ``LAMINARIO_TEST_TMP`` when set (a scratch drive, never the
system drive), else ``.tmp/pytest`` inside the repository, which git ignores.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    if config.option.basetemp is None:
        base = Path(os.environ.get("LAMINARIO_TEST_TMP") or ROOT / ".tmp" / "pytest")
        base.parent.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(base)
