"""Build the mineral vocabulary (app/collections/data/vocab/minerals.json) from its two sources.

1. **The IMA list** ("The New IMA List of Minerals, a work in progress", the CNMNC's PDF, CC BY-SA 3.0): every valid
   species with its IMA status. The table is read with pypdf; a row is a name, the CNMNC formula, the status
   (A, G, Rd, Rn, Q) and the IMA number or year. Long formulas wrap onto the next line and a few names are printed
   against their formula; both are handled and the count is reported.
2. **Wikidata** (CC0): the Nickel-Strunz code of each mineral item (P713 "10th ed", else P712 "9th edition") and its
   crystal system (P556), from the SPARQL result saved beside the PDF (query: wikidata-nickel-strunz.rq). Items are
   joined to IMA names by English label or alias, case-insensitively; then by IMA number.

The group names of ``mineral_groups.yaml`` are resolved against the same extract. Nothing is fetched here: the
inputs live in the data vault (``LAMINARIO_FIXTURES/vocab``) with their SHA-256 recorded in the output.

    python scripts/build_minerals.py --vault E:/_Datos/laminario [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "collections" / "data" / "vocab" / "minerals.json"
GROUPS = ROOT / "app" / "collections" / "data" / "vocab" / "mineral_groups.yaml"
IMA_PDF = "vocab/ima-list-2026-01.pdf"
WIKIDATA = "vocab/wikidata-nickel-strunz-2026-09-29.json"
QUERY = "vocab/wikidata-nickel-strunz.rq"

UPPER = "A-Z\u00c0-\u00de\u0100-\u017f"
NAME = r"([" + UPPER + r"](?:'|[a-z\u00df-\u00ff\u0100-\u017f])[^\s]*)"
STATUS = re.compile(r"\s(A|G|Rd|Rn|Q)\s(\?|\d{4}(?:-\d{2,3}a?)?(?:\s?s\.p\.)?)")
POLYTYPE = re.compile(r"^(\S+-\d+N)(')?\s(')?(\d+S)\s")
GLUED = re.compile(r"^(.*?[a-z\)])((?:[A-Z\[\(\u2610]).*)$")
CODE = re.compile(r"^(\d{1,2})\.([A-Z0-9])([A-Z0-9])?\.?(\d{2}[a-z]?)?$")
SYSTEMS = ("triclinic", "monoclinic", "orthorhombic", "tetragonal", "trigonal", "hexagonal", "cubic")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ima_rows(pdf: Path) -> list[dict]:
    """The species rows of the IMA list, in the order printed."""
    lines: list[str] = []
    for page in PdfReader(str(pdf)).pages[2:]:
        lines += page.extract_text().splitlines()
    rows, pending = [], None
    for line in lines:
        # Polytype names are printed with their suffix split ("-2N 2S", "-2N '2S"); join them back.
        line = POLYTYPE.sub(lambda m: m.group(1) + (m.group(2) or m.group(3) or "") + m.group(4) + " ", line)
        status = STATUS.search(line + " ")
        named = re.match(r"^" + NAME + r"(?:\s+(.*))?$", line)
        if named and status and status.start() >= len(named.group(1)):
            name = named.group(1)
            formula = line[len(name):status.start()].strip()
            if not formula:
                glued = GLUED.match(name)
                if glued and "-" in glued.group(1):
                    name, formula = glued.group(1), glued.group(2)
            rows.append({"name": name, "formula": formula, "status": status.group(1), "year": status.group(2)})
            pending = None
        elif pending and (lead := STATUS.search(" " + line + " ")):
            # A wrapped row: the status may open the line that ends it.
            rows.append({"name": pending[0], "formula": (pending[1] + " " + line[:max(lead.start() - 1, 0)]).strip(),
                         "status": lead.group(1), "year": lead.group(2)})
            pending = None
        elif named and not status and named.group(2) and not re.search(r"\(\d{4}\)|,\s*\d+$", line):
            pending = (named.group(1), named.group(2).strip())
        elif status:
            pending = None
    for row in rows:
        # "Baumhauerite II", a questionable polytype, is printed as a name and a roman numeral.
        if row["formula"].startswith("II "):
            row["name"] += " II"
            row["formula"] = row["formula"][3:]
    return rows


def wikidata_index(path: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """Codes and systems by lower-case label, and codes by IMA number (hyphenated numbers only)."""
    by_name: dict[str, dict] = {}
    by_number: dict[str, dict] = {}
    for b in json.loads(path.read_text(encoding="utf-8"))["results"]["bindings"]:
        entry = by_name.setdefault(b["name"]["value"].lower(), {"ns9": set(), "ns10": set(), "sys": set()})
        for key in ("ns9", "ns10"):
            if key in b:
                entry[key].add(b[key]["value"].strip())
        if "sys" in b:
            entry["sys"].add(b["sys"]["value"])
        if "ima" in b:
            number = re.sub(r"^IMA\s*", "", b["ima"]["value"]).strip()
            if re.fullmatch(r"\d{4}-\d{3}[a-z]?", number):
                num = by_number.setdefault(number, {"ns9": set(), "ns10": set(), "sys": set()})
                for key in ("ns9", "ns10"):
                    if key in b:
                        num[key].add(b[key]["value"].strip())
    return by_name, by_number


def one_code(entry: dict | None) -> str | None:
    """The single Nickel-Strunz code of an entry (10th ed first); None when absent or ambiguous."""
    if not entry:
        return None
    for key in ("ns10", "ns9"):
        codes = {c for c in entry[key] if CODE.match(c)}
        if len(codes) == 1:
            return codes.pop()
        if len(codes) > 1:
            return None
    return None


def one_system(entry: dict | None) -> str | None:
    if not entry:
        return None
    found = {s for s in SYSTEMS for label in entry["sys"] if label.startswith(s)}
    return found.pop() if len(found) == 1 else None


def cut(code: str, level: str) -> str:
    """A Nickel-Strunz code cut to a level: class 9, division 9.F, subdivision 9.FA, group 9.FA.35."""
    m = CODE.match(code)
    klass, division, subdivision, group = m.groups()
    if level == "class":
        return klass
    if level == "division":
        return f"{klass}.{division}"
    if level == "subdivision":
        return f"{klass}.{division}{subdivision or ''}"
    return code


def build(vault: Path) -> dict:
    pdf, wikidata, query = vault / IMA_PDF, vault / WIKIDATA, vault / QUERY
    rows = ima_rows(pdf)
    by_name, by_number = wikidata_index(wikidata)
    groups = yaml.safe_load(GROUPS.read_text(encoding="utf-8"))
    species_codes = groups.get("species_codes", {})
    species = []
    coded = 0
    names = {r["name"] for r in rows}
    for r in rows:
        entry = by_name.get(r["name"].lower())
        code = one_code(entry)
        if code is None and re.fullmatch(r"\d{4}-\d{3}a?", r["year"].split(" ")[0]):
            code = one_code(by_number.get(r["year"].split(" ")[0]))
        if code is None and r["name"] in species_codes:
            code = one_code(by_name.get(species_codes[r["name"]]["member"].lower()))
        coded += code is not None
        species.append([r["name"], r["status"], code, one_system(entry)])
    out_groups = []
    for name, spec in groups["groups"].items():
        if spec.get("wikidata"):
            code = one_code(by_name.get(name.lower()))
            origin = "wikidata"
        else:
            member = spec["member"]
            if member not in names:
                raise SystemExit(f"group {name}: member {member} is not an IMA species")
            code = one_code(by_name.get(member.lower()))
            code = cut(code, spec.get("level", "group")) if code else None
            origin = f"member:{member}"
        if not code:
            raise SystemExit(f"group {name}: no Nickel-Strunz code found")
        out_groups.append([name, code, origin])
    for alias, target in groups.get("synonyms", {}).items():
        if target not in names:
            raise SystemExit(f"synonym {alias}: {target} is not an IMA species")
    return {
        "about": "Mineral names for mineral anchors. Species, statuses: the IMA list (CC BY-SA 3.0). Nickel-Strunz "
                 "codes and crystal systems: Wikidata P713/P712 and P556 (CC0). Built by scripts/build_minerals.py.",
        "licence": "https://creativecommons.org/licenses/by-sa/3.0/",
        "sources": {
            "ima": {"title": "The New IMA List of Minerals, a work in progress, updated January 2026",
                    "url": "https://cnmnc.units.it/", "file": pdf.name, "sha256": sha256(pdf)},
            "wikidata": {"title": "Wikidata SPARQL: Nickel-Strunz codes (P712, P713) and crystal system (P556)",
                         "url": "https://query.wikidata.org/", "retrieved_on": "2026-09-29", "file": wikidata.name,
                         "sha256": sha256(wikidata), "query_sha256": sha256(query)},
        },
        "counts": {"species": len(species), "with_code": coded, "groups": len(out_groups)},
        "species_columns": ["name", "ima_status", "nickel_strunz", "crystal_system"],
        "species": species,
        "group_columns": ["name", "nickel_strunz", "code_from"],
        "groups": out_groups,
        "synonyms": groups.get("synonyms", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--vault", type=Path, required=True, help="the data vault holding vocab/")
    parser.add_argument("--check", action="store_true", help="fail if the committed file differs from a rebuild")
    args = parser.parse_args()
    data = build(args.vault)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace('],["', '],\n["') + "\n"
    if args.check:
        if OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT.relative_to(ROOT)} differs from a rebuild")
            return 1
        print("minerals.json matches its sources")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    c = data["counts"]
    print(f"{c['species']} species ({c['with_code']} with a Nickel-Strunz code), {c['groups']} group names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
