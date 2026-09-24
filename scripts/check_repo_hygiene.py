#!/usr/bin/env python3
"""Fail when the repository tracks something that belongs outside git.

Laminario handles files that are large, private or machine-specific: scanner slides (NDPI, SVS,
MRXS, ...), pyramidal TIFFs, the contributors' database, the local environment. None of them may be
committed. This guard reads ``git ls-files`` and fails on:

- a real ``.env`` (only ``.env.example`` is allowed);
- a virtual environment or a native binary;
- heavy data formats and every slide or pyramid format the product reads or writes;
- a SQLite database file;
- any tracked file larger than ``MAX_BYTES``;
- a leaked local machine path in a text file.

Standard library only, so it runs before any install. Usage: ``python scripts/check_repo_hygiene.py``.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = "scripts/check_repo_hygiene.py"

#: 5 MB. The largest legitimate tracked files are icons, fonts and documentation figures.
MAX_BYTES = 5 * 1024 * 1024

ENV_FILE = re.compile(r"(^|/)\.env(\..+)?$")
VENV_PATH = re.compile(r"(^|/)\.?venv[^/]*/", re.IGNORECASE)
NATIVE_BINARY = re.compile(r"\.(dll|so|dylib|exe|pyd|pt|pth|onnx)$", re.IGNORECASE)
HEAVY_DATA = re.compile(r"\.(parquet|h5|hdf5|nc|mat|npy|npz|feather|zarr)$", re.IGNORECASE)
SLIDE_OR_PYRAMID = re.compile(
    r"\.(ndpi|vms|vmu|svs|svslide|mrxs|scn|vsi|bif|czi|dcm|tif|tiff|btf|jp2|j2k|isyntax|dzi)$",
    re.IGNORECASE,
)
DATABASE = re.compile(r"\.(sqlite|sqlite3|db)(-wal|-shm|-journal)?$", re.IGNORECASE)

#: Local paths that identify the owner's machines. Written split so this file does not match itself.
LOCAL_PATHS = ("D:" + "\\_Repos", "E:" + "\\_", "C:" + "\\Users\\")
TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".ts", ".tsx", ".js", ".mjs",
    ".cjs", ".css", ".html", ".ps1", ".sh", ".ini", ".cfg", ".svg", ".example",
}


def path_problems(path: str) -> list[str]:
    """Return every reason a tracked path is not allowed. Empty when the path is fine."""
    problems: list[str] = []
    if ENV_FILE.search(path) and not path.endswith(".env.example"):
        problems.append("a real .env is tracked (only .env.example may be)")
    if VENV_PATH.search(path):
        problems.append("a virtual environment is tracked")
    if NATIVE_BINARY.search(path):
        problems.append("a native binary or model weight file is tracked")
    if HEAVY_DATA.search(path):
        problems.append("a heavy data format is tracked")
    if SLIDE_OR_PYRAMID.search(path):
        problems.append("a slide or pyramid image file is tracked (source and served images live outside git)")
    if DATABASE.search(path):
        problems.append("a database file is tracked (the contributors' database never enters git)")
    return problems


def content_problems(path: str, text: str) -> list[str]:
    """Return a reason for every leaked local machine path in a text file."""
    return [f"leaked local path {marker!r}" for marker in LOCAL_PATHS if marker in text]


def tracked_files(root: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True)
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def check(root: Path) -> list[str]:
    findings: list[str] = []
    for rel in tracked_files(root):
        if rel == SELF:
            continue
        for problem in path_problems(rel):
            findings.append(f"{rel}: {problem}")
        full = root / rel
        if not full.is_file():
            continue
        size = full.stat().st_size
        if size > MAX_BYTES:
            findings.append(f"{rel}: {size / 1e6:.1f} MB exceeds the {MAX_BYTES / 1e6:.0f} MB limit for tracked files")
        if full.suffix.lower() in TEXT_SUFFIXES or full.name == ".env.example":
            text = full.read_text(encoding="utf-8", errors="ignore")
            findings.extend(f"{rel}: {p}" for p in content_problems(rel, text))
    return findings


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else ROOT
    findings = check(root)
    if findings:
        print("::error::repository hygiene failed:")
        for finding in findings:
            print(f"  {finding}")
        return 1
    print("check_repo_hygiene: OK: nothing that belongs outside git is tracked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
