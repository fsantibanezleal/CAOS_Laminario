"""Anchor vocabularies: what a rock, mineral, crystal or material anchor may name, and where it places.

Each non-taxon anchor resolves to a **path**, a dotted string the tree's rules match by prefix:

- rock: the term's family from ``rocks.yaml`` (``igneous.coarse``, ``sedimentary.carbonate``, ``meteorite``);
- mineral: the Nickel-Strunz code as class, division, subdivision and group (``9.AF.15`` is ``9.A.F.15``), from the
  mineral table, or the class the submission declares for a species the table has no code for;
- crystal: the origin, and for ice the Kikuchi general category (``ice.P``);
- material: the term's family (``fibre``, ``pollen-sample``).

Names are matched without regard to case, spaces or hyphens where the vocabulary allows it, and every result
carries the canonical form that is stored.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

DATA = Path(__file__).resolve().parent / "data" / "vocab"
STRUNZ = re.compile(r"^0?(\d{1,2})(?:\.([A-Z0-9])?([A-Z0-9])?\.?(\d{2}[a-z]?)?)?$")


def _yaml(name: str) -> dict:
    return yaml.safe_load((DATA / name).read_text(encoding="utf-8"))


def strunz_path(code: str) -> str | None:
    """A Nickel-Strunz code as a dotted path: ``9.AF.15`` to ``9.A.F.15``, ``9.FA`` to ``9.F.A``, ``10`` to ``10``."""
    m = STRUNZ.match(code.strip())
    if not m:
        return None
    klass = int(m.group(1))
    if not 1 <= klass <= 10:
        return None
    return ".".join([str(klass)] + [part for part in m.groups()[1:] if part])


def prefix_of(prefix: str, path: str) -> bool:
    """Whether a dotted path starts with a dotted prefix, segment by segment (``1`` is not a prefix of ``10``)."""
    return path == prefix or path.startswith(prefix + ".")


def kebab(text: str) -> str:
    return re.sub(r"[\s_]+", "-", text.strip().lower())


@dataclass(frozen=True)
class Term:
    """A resolved non-taxon anchor."""

    ref: str
    rank: str | None
    path: str
    classification: str | None = None


@dataclass(frozen=True)
class Problem:
    field: str
    message: str
    expected: str


@dataclass(frozen=True)
class Vocabularies:
    rocks: dict[str, dict]
    rock_synonyms: dict[str, str]
    rock_sources: dict[str, str]
    minerals: dict[str, list]
    mineral_groups: dict[str, list]
    mineral_synonyms: dict[str, str]
    mineral_about: dict
    parts: dict[str, dict]
    materials: dict[str, dict]
    material_families: dict[str, dict]
    crystal_origins: dict[str, dict]
    crystal_systems: dict[str, dict]
    kikuchi: dict[str, dict]
    preparations: dict[str, dict]
    modalities: dict[str, dict]

    def rock_paths(self) -> set[str]:
        """Every family and every prefix of one (``sedimentary`` as well as ``sedimentary.carbonate``)."""
        paths: set[str] = set()
        for term in self.rocks.values():
            bits = term["family"].split(".")
            paths.update(".".join(bits[:i]) for i in range(1, len(bits) + 1))
        return paths

    def material_paths(self) -> set[str]:
        return set(self.material_families)

    def crystal_paths(self) -> set[str]:
        return set(self.crystal_origins) | {f"ice.{k}" for k in self.kikuchi}

    def mineral_paths(self) -> set[str]:
        """Every prefix of every known mineral path, so a rule can name a class, division or group."""
        paths: set[str] = set()
        for code in [row[2] for row in self.minerals.values() if row[2]] + [g[1] for g in self.mineral_groups.values()]:
            path = strunz_path(code)
            if path:
                bits = path.split(".")
                paths.update(".".join(bits[:i]) for i in range(1, len(bits) + 1))
        return paths


@lru_cache(maxsize=1)
def load() -> Vocabularies:
    rocks = _yaml("rocks.yaml")
    minerals = json.loads((DATA / "minerals.json").read_text(encoding="utf-8"))
    parts = _yaml("parts.yaml")
    materials = _yaml("materials.yaml")
    crystals = _yaml("crystals.yaml")
    facets = _yaml("facets.yaml")
    return Vocabularies(
        rocks=rocks["terms"],
        rock_synonyms=rocks.get("synonyms") or {},
        rock_sources=rocks["source_labels"],
        minerals={row[0].lower(): row for row in minerals["species"]},
        mineral_groups={row[0].lower(): row for row in minerals["groups"]},
        mineral_synonyms={k.lower(): v for k, v in (minerals.get("synonyms") or {}).items()},
        mineral_about={k: minerals[k] for k in ("about", "licence", "sources", "counts")},
        parts=parts["terms"],
        materials=materials["terms"],
        material_families=materials["families"],
        crystal_origins=crystals["origins"],
        crystal_systems=crystals["systems"],
        kikuchi=crystals["kikuchi"],
        preparations=facets["preparation"],
        modalities=facets["modality"],
    )


MINERAL_CLASS_EXPECTED = "its Nickel-Strunz class, 1 to 10, or a longer code such as 9.AF.15"


def resolve_term(kind: str, ref: str, classification: str | None = None,
                 field: str = "specimen.anchor") -> Term | Problem:
    """Resolve a rock, mineral, crystal or material anchor to its canonical form and path."""
    v = load()
    if kind == "rock":
        key = kebab(ref)
        key = v.rock_synonyms.get(key, key)
        if key not in v.rocks:
            return Problem(f"{field}.ref", f"{ref} is not a rock name of the vocabulary",
                           "a name of the BGS Rock Classification Scheme, a meteorite class or a Laminario rock term")
        if classification:
            return Problem(f"{field}.classification", "a rock takes no classification", "no classification")
        return Term(key, None, v.rocks[key]["family"])
    if kind == "mineral":
        name = ref.strip().lower()
        name = v.mineral_synonyms.get(name, name).lower()
        declared = strunz_path(classification) if classification else None
        if classification and declared is None:
            return Problem(f"{field}.classification", f"{classification} is not a Nickel-Strunz code",
                           MINERAL_CLASS_EXPECTED)
        if name in v.minerals:
            row = v.minerals[name]
            known = strunz_path(row[2]) if row[2] else None
            if known and declared:
                if not (prefix_of(declared, known) or prefix_of(known, declared)):
                    return Problem(f"{field}.classification",
                                   f"{row[0]} is {row[2]} in Nickel-Strunz, not {classification}",
                                   f"{row[2]}, or no classification")
                known = max(known, declared, key=len)
            path = known or declared
            if path is None:
                return Problem(f"{field}.classification", f"no Nickel-Strunz class is recorded for {row[0]}",
                               MINERAL_CLASS_EXPECTED)
            return Term(row[0], "species", path, row[2] or classification)
        if name in v.mineral_groups:
            row = v.mineral_groups[name]
            return Term(row[0], "group", strunz_path(row[1]), row[1])
        return Problem(f"{field}.ref", f"{ref} is not on the IMA list of minerals",
                       "an IMA mineral species or a common group name such as olivine or plagioclase")
    if kind == "crystal":
        origin, _, system = kebab(ref).partition("/")
        if origin not in v.crystal_origins:
            return Problem(f"{field}.ref", f"{ref} does not start with a crystal origin",
                           "an origin (" + ", ".join(v.crystal_origins) + "), optionally /system")
        if system and system not in v.crystal_systems:
            return Problem(f"{field}.ref", f"{system} is not a crystal system", ", ".join(v.crystal_systems))
        path = origin
        if classification:
            if origin != "ice":
                return Problem(f"{field}.classification", "only ice and snow crystals take a category",
                               "no classification")
            if classification.upper() not in v.kikuchi:
                return Problem(f"{field}.classification", f"{classification} is not a general category",
                               "one of: " + ", ".join(v.kikuchi))
            classification = classification.upper()
            path = f"ice.{classification}"
        return Term(origin + (f"/{system}" if system else ""), None, path, classification)
    if kind == "material":
        key = kebab(ref)
        if key not in v.materials:
            return Problem(f"{field}.ref", f"{ref} is not a material of the vocabulary",
                           "a material term such as cotton, potato-starch or microplastic-fibre")
        if classification:
            return Problem(f"{field}.classification", "a material takes no classification", "no classification")
        return Term(key, None, v.materials[key]["family"])
    return Problem(f"{field}.kind", f"{kind} is not resolved by a vocabulary", "rock, mineral, crystal or material")


def check_part(part: str | None) -> Problem | None:
    if part is not None and part not in load().parts:
        return Problem("specimen.part", f"{part} is not a part of the vocabulary",
                       "a part such as blood, feather, leaf or pollen")
    return None


def search(kind: str, query: str, limit: int = 20) -> list[dict]:
    """Vocabulary entries whose name starts with the query (then contains it), for the anchor field."""
    v = load()
    q = query.strip().lower()
    if not q:
        return []
    if kind == "mineral":
        rows = [(r[0], "species", r[2]) for r in v.minerals.values()] + \
               [(g[0], "group", g[1]) for g in v.mineral_groups.values()]
        items = [{"ref": n, "name": n, "rank": rank, "classification": code} for n, rank, code in rows]
    elif kind == "rock":
        items = [{"ref": k, "name": k.replace("-", " "), "rank": None, "classification": None} for k in v.rocks]
    elif kind == "material":
        items = [{"ref": k, "name": t["en"], "rank": None, "classification": None} for k, t in v.materials.items()]
    elif kind == "crystal":
        items = [{"ref": k, "name": o["en"], "rank": None, "classification": None}
                 for k, o in v.crystal_origins.items()]
    else:
        return []
    starts = [i for i in items if i["name"].lower().startswith(q) or i["ref"].lower().startswith(q)]
    contains = [i for i in items if i not in starts and (q in i["name"].lower() or q in i["ref"].lower())]
    ranked = sorted(starts, key=lambda i: (len(i["name"]), i["name"])) + sorted(contains, key=lambda i: i["name"])
    return ranked[:limit]
