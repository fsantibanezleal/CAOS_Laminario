"""Load libvips (with OpenSlide) once, the same way on every machine.

On Windows the official ``vips-dev-x64-all`` build (which includes OpenSlide) sits in a folder named by
``LAMINARIO_VIPS_BIN``; that folder is added to the DLL search path before ``pyvips`` imports the library.
On Linux the distribution's libvips (built against OpenSlide on Ubuntu) is found on its own and the variable
stays unset. ``pyvips`` is installed without its binary extra so it never shadows the chosen library.

Import ``vips()`` instead of ``pyvips`` anywhere in the engine: it performs the setup and reports, once,
whether the build can read scanner formats.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ENV_VAR = "LAMINARIO_VIPS_BIN"


@dataclass(frozen=True)
class LibraryInfo:
    version: str
    openslide: bool
    bin_dir: str | None


@lru_cache
def vips():
    """The ``pyvips`` module, with the library located per the environment."""
    bin_dir = os.environ.get(ENV_VAR)
    if bin_dir:
        folder = Path(bin_dir)
        if not folder.is_dir():
            raise RuntimeError(f"{ENV_VAR} points to {bin_dir}, which is not a folder")
        os.add_dll_directory(str(folder))
        os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")
    import pyvips

    return pyvips


@lru_cache
def info() -> LibraryInfo:
    module = vips()
    version = ".".join(str(module.version(i)) for i in range(3))
    has_openslide = module.type_find("VipsForeign", "openslideload") != 0
    return LibraryInfo(version=version, openslide=has_openslide, bin_dir=os.environ.get(ENV_VAR))
