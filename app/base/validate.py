"""Validation: every lock entry through the same checks a contribution meets, offline, with a committed report.

For each slide: the ingestion contract (``validate_submission``, origin ``base``: licences of the base policy, a
complete source block per asset), then the collection tree's checks (``check_submission``: the anchor and the host
resolve, the part exists, the placement accepts it) against a throw-away database seeded from ``data/base/taxa.json``
so no network is used, then the base-collection floors (dossier 06, section 4). The report is
``docs/collections/base-report.md``.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.base import coverage
from app.base.acquire import load as load_acquired
from app.base.lock import LOCK, TAXA
from app.base.submission import source_path, submission
from app.collections import taxa as taxa_cache
from app.collections.service import check_submission
from app.collections.tree import load_tree
from app.contracts.ingest import validate_submission
from app.db.engine import async_sessions, make_async_engine
from app.db.migrate import upgrade_to_head
from app.db.models import Taxon
from app.imaging import reader
from app.imaging.guards import ImageRefused

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT = ROOT / "docs" / "collections" / "base-report.md"
FLOORS = {"slides": 300, "per_collection": 12, "wsi": 14}
ROCK_FAMILIES = ("igneous", "sedimentary", "metamorphic")
#: Collections whose open supply, after curation, is below the per-collection floor, each with the finding that
#: records the searches made. A collection below the floor that is not listed here fails validation.
SHORTFALLS = {
    "life.reptiles": "F-031: the open, licence-compatible reptile micrographs found on Commons, the Wellcome "
                     "Collection and GBIF are seven single images; the rest are multi-panel figures or fossils",
}


@dataclass
class Result:
    slide_id: str
    collection: str
    node: str
    errors: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    wsi: bool = False
    polarised_pair: bool = False
    rock_family: str | None = None


async def _seeded_session(folder: Path):
    database = folder / "validate.sqlite3"
    upgrade_to_head(database)
    engine = make_async_engine(database)
    rows = json.loads(TAXA.read_text(encoding="utf-8")) if TAXA.exists() else {}
    async with async_sessions(engine)() as db:
        for t in rows.values():
            db.add(Taxon(key=t["key"], name=t["name"] or str(t["key"]), rank=t["rank"] or "", status=t["status"],
                         accepted_key=t["accepted_key"], lineage_json=json.dumps(t["lineage"])))
        await db.commit()
    return engine


def check(slides: list[dict], acquired: dict[str, dict], vault: Path | None,
          workdir: Path | None = None) -> list[Result]:
    """Every slide through the checks; the throw-away database goes in ``workdir`` (default: the vault)."""
    tree = load_tree()
    base = workdir or (vault / "tmp" if vault else None)
    if base is not None:
        base.mkdir(parents=True, exist_ok=True)

    async def run() -> list[Result]:
        with tempfile.TemporaryDirectory(prefix="laminario-validate-", dir=base) as tmp:
            engine = await _seeded_session(Path(tmp))
            offline = taxa_cache.new_client("http://127.0.0.1:9/v1")
            results = []
            try:
                async with async_sessions(engine)() as db:
                    for slide in slides:
                        results.append(await _one(db, offline, slide, acquired, vault, tree))
            finally:
                await offline.aclose()
                await engine.dispose()
            return results

    return asyncio.run(run())


async def _one(db, client, slide, acquired, vault, tree) -> Result:
    result = Result(slide["id"], slide["collection"], slide["placement"]["node"])
    result.wsi = any(a.get("wsi") for a in slide["assets"])
    states = {a.get("polarisation", {}).get("state") for a in slide["assets"] if a["role"] == "polarised"}
    result.polarised_pair = {"ppl", "xpl"} <= states
    if slide["specimen"]["anchor"]["kind"] == "rock":
        result.rock_family = result.node.split(".")[2] if result.node.count(".") >= 2 else None
    missing = [a["url"] for a in slide["assets"] if a["url"] not in acquired]
    if missing:
        result.errors.append(f"not acquired: {', '.join(missing)}")
        return result
    if vault is not None:
        # Every source file through the imaging engine's header checks, as its processing will read it: a source the
        # product refuses is found here, not by a failed job hours into a bake (Philips-2, 2026-09-30).
        for asset in slide["assets"]:
            path = source_path(asset, acquired, vault)
            if not path.is_file():
                result.errors.append(f"not in the vault: {asset['url']}")
                continue
            try:
                reader.read_info(path)
            except ImageRefused as exc:
                result.errors.append(f"refused by the imaging engine: {exc} ({asset['url']})")
        if result.errors:
            return result
    try:
        payload = submission(slide, acquired, vault)
    except (OSError, ValueError) as exc:
        result.errors.append(f"cannot expand: {exc}")
        return result
    report = validate_submission(payload)
    result.errors += [f"{e['field']}: {e['message']} (expected {e['expected']})" for e in report.errors]
    result.flags += [f["code"] for f in report.flags]
    if report.valid:
        try:
            checked = await check_submission(db, client, report.submission, tree=tree)
        except taxa_cache.TaxonServiceUnavailable:
            result.errors.append("a taxon is not in data/base/taxa.json")
        else:
            result.errors += [f"{e['field']}: {e['message']} (expected {e['expected']})" for e in checked.errors]
    return result


def collections() -> list[str]:
    return [n.id for n in load_tree().nodes.values() if n.level == "collection"]


def floors(results: list[Result]) -> dict[str, object]:
    per = Counter(r.collection for r in results)
    pairs = {f for r in results if r.polarised_pair and r.rock_family for f in [r.rock_family]}
    below = sorted(c for c in collections() if per.get(c, 0) < FLOORS["per_collection"])
    return {
        "slides": len(results),
        "per_collection": {c: per.get(c, 0) for c in collections()},
        "collections_below_floor": below,
        "undocumented_shortfalls": [c for c in below if c not in SHORTFALLS],
        "wsi": sum(r.wsi for r in results),
        "rock_families_with_pairs": sorted(pairs),
    }


def floor_problems(summary: dict) -> list[str]:
    """The floors of dossier 06 that the collection misses (a recorded shortfall is not a problem)."""
    problems = []
    if summary["slides"] < FLOORS["slides"]:
        problems.append(f"{summary['slides']} slides, fewer than {FLOORS['slides']}")
    if summary["wsi"] < FLOORS["wsi"]:
        problems.append(f"{summary['wsi']} whole-slide images, fewer than {FLOORS['wsi']}")
    problems += [f"{c} holds {summary['per_collection'][c]} slides and no recorded reason"
                 for c in summary["undocumented_shortfalls"]]
    missing = [f for f in ROCK_FAMILIES if f not in summary["rock_families_with_pairs"]]
    if missing:
        problems.append(f"no polarised pair for {', '.join(missing)}")
    return problems


def validate(vault: Path | None) -> tuple[list[Result], dict]:
    lock = yaml.safe_load(LOCK.read_text(encoding="utf-8"))
    results = check(lock["slides"], load_acquired(), vault)
    summary = floors(results)
    write_report(results, summary)
    coverage.write(lock["slides"])
    return results, summary


def write_report(results: list[Result], summary: dict) -> None:
    failed = [r for r in results if r.errors]
    lines = [
        "# The base collection: validation report",
        "",
        "Generated by `python -m app.base validate` from `data/base/lock.yaml`; do not edit by hand. Every slide goes "
        "through the ingestion contract and the collection tree's checks offline, as a contribution would.",
        "",
        f"- Slides: **{summary['slides']}** (floor {FLOORS['slides']})",
        f"- Whole-slide images: **{summary['wsi']}** (floor {FLOORS['wsi']})",
        f"- Rock families with a registered PPL/XPL pair: {', '.join(summary['rock_families_with_pairs']) or 'none'}"
        f" (all of {', '.join(ROCK_FAMILIES)} required)",
        f"- Collections below {FLOORS['per_collection']} slides: "
        f"{', '.join(summary['collections_below_floor']) or 'none'}"
        + "".join(f"\n  - `{c}`: {SHORTFALLS[c]}" for c in summary["collections_below_floor"] if c in SHORTFALLS),
        f"- Collections below the floor with no recorded reason: "
        f"{', '.join(summary['undocumented_shortfalls']) or 'none'}",
        f"- Slides failing a check: **{len(failed)}**",
        "",
        "| Collection | Slides |",
        "|---|---|",
    ]
    lines += [f"| `{c}` | {n} |" for c, n in summary["per_collection"].items()]
    lines += ["", "## Every slide", "", "| Slide | Placed at | Result |", "|---|---|---|"]
    for r in results:
        verdict = "; ".join(r.errors) if r.errors else ("pass" + (f" (flags: {', '.join(sorted(set(r.flags)))})"
                                                                  if r.flags else ""))
        lines.append(f"| `{r.slide_id}` | `{r.node}` | {verdict} |")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
