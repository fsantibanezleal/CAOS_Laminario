"""Check that every rock term sourced from the BGS Rock Classification Scheme occurs in its volume.

rocks.yaml marks each term with its source (rcs-1 igneous, rcs-2 metamorphic, rcs-3 sedimentary). This reads the
three PDFs from the data vault (``vocab/bgs-rcs-{igneous,metamorphic,sedimentary}.pdf``), joins words broken
across lines, and looks for each term with hyphens and spaces treated alike (``broken-rock`` matches "Broken Rock",
``melilite-bearing-ultramafic-volcanic-rock`` matches "melilite-bearing ultramafic volcanic rocks"), or for the
form the volume prints when its appendix wraps a name across a line (``printed``).

    python scripts/check_rock_terms.py --vault E:/_Datos/laminario
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
ROCKS = ROOT / "app" / "collections" / "data" / "vocab" / "rocks.yaml"
VOLUMES = {"rcs-1": "bgs-rcs-igneous.pdf", "rcs-2": "bgs-rcs-metamorphic.pdf", "rcs-3": "bgs-rcs-sedimentary.pdf"}


def volume_text(pdf: Path) -> str:
    text = "\n".join(page.extract_text() for page in PdfReader(str(pdf)).pages).lower()
    text = re.sub(r"-\s*\n\s*", "-", text)  # a hyphenated name broken at the line end
    return re.sub(r"\s+", " ", text)


def missing_terms(vault: Path) -> list[str]:
    terms = yaml.safe_load(ROCKS.read_text(encoding="utf-8"))["terms"]
    texts = {source: volume_text(vault / "vocab" / name) for source, name in VOLUMES.items()}
    missing = []
    for term, entry in terms.items():
        text = texts.get(entry["source"])
        if text is None:
            continue
        printed = entry.get("printed", "").lower()
        if printed and printed in text:
            continue
        if term.replace("-", " ") not in text.replace("-", " "):
            missing.append(f"{term} ({entry['source']})")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--vault", type=Path, required=True)
    args = parser.parse_args()
    missing = missing_terms(args.vault)
    for term in missing:
        print(f"not found in its volume: {term}")
    print(f"{len(missing)} rock terms not found")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
