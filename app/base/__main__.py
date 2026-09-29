"""The base-collection lane: ``python -m app.base <step> ...``.

    harvest [collection...]   list candidates per data/base/harvest.yaml into the vault, with review sheets
    select                    expand the curator's picks (data/base/picks/*.txt) into data/base/selection.yaml
    lock                      build data/base/lock.yaml from the selection (GBIF names and lineages resolved)
    acquire [slide|collection...]   download every image once into the vault; record SHA-256 and date
    validate                  run every lock slide through the contract and the tree; write the report
    bake --out DIR [slide|collection...]   process the collection into DIR with the product's pipeline
    import --bake DIR         verify a bake and load it into this deployment's database and store
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from app.base import review
from app.base.http import Polite
from app.base.sources import commons, nhm, smithsonian
from app.config import get_settings

ROOT = Path(__file__).resolve().parent.parent.parent
HARVEST = ROOT / "data" / "base" / "harvest.yaml"


def vault() -> Path:
    fixtures = get_settings().fixtures
    if not fixtures:
        raise SystemExit("LAMINARIO_FIXTURES names the data vault; the base lane writes only there")
    return Path(fixtures) / "base"


def harvest(collections: list[str]) -> None:
    spec = yaml.safe_load(HARVEST.read_text(encoding="utf-8"))
    out_dir = vault() / "candidates"
    out_dir.mkdir(parents=True, exist_ok=True)
    with Polite() as http:
        for name in collections or list(spec):
            found: list[dict] = []
            seen: set[tuple[str, str]] = set()
            for item in spec[name]:
                if "commons" in item:
                    got, counts = commons.harvest(http, item["commons"], depth=item.get("depth", 1),
                                                  min_side=item.get("min_side", 1000), limit=item.get("limit", 120))
                elif "smithsonian" in item:
                    got, counts = smithsonian.harvest(http, item["smithsonian"], limit=item.get("limit", 100),
                                                      title_contains=item.get("title_contains"))
                elif "commons_files" in item:
                    pages = commons.named(http, item["commons_files"])
                    got = [c for c in (commons.candidate(pg, "named", item.get("min_side", 1000)) for pg in pages) if c]
                    counts = {"files": len(pages), "kept": len(got)}
                else:
                    got, counts = nhm.harvest(http, item["nhm"], item.get("filters"), limit=item.get("limit", 60),
                                              need_micro=item.get("need_micro", True))
                print(f"{name}: {item} -> {counts}", flush=True)
                for c in got:
                    key = (c["source"], str(c["record_id"]))
                    if key not in seen:
                        seen.add(key)
                        found.append(c)
            path = out_dir / f"{name}.jsonl"
            path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in found), encoding="utf-8")
            review.sheet(found, out_dir / f"{name}.png", title=name)
            print(f"{name}: {len(found)} candidates -> {path}", flush=True)


def main() -> int:
    # Record titles and names are printed as they are (Cyrillic, accents); a Windows console would refuse them.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="python -m app.base")
    sub = parser.add_subparsers(dest="step", required=True)
    sub.add_parser("harvest").add_argument("collections", nargs="*")
    sub.add_parser("select")
    sub.add_parser("lock")
    sub.add_parser("acquire").add_argument("only", nargs="*")
    sub.add_parser("validate")
    b = sub.add_parser("bake")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("only", nargs="*")
    i = sub.add_parser("import")
    i.add_argument("--bake", type=Path, required=True)
    args = parser.parse_args()
    if args.step == "harvest":
        harvest(args.collections)
    elif args.step == "select":
        from app.base import picks

        selection = picks.write_selection(ROOT / "data" / "base" / "picks", vault(),
                                          ROOT / "data" / "base" / "selection.yaml")
        print({k: len(v) for k, v in selection.items()})
    elif args.step == "lock":
        from app.base import lock

        built = lock.build(vault())
        print(f"{len(built['slides'])} slides locked")
    elif args.step == "acquire":
        from app.base import acquire

        acquire.acquire(vault(), set(args.only) or None)
    elif args.step == "validate":
        from app.base import validate

        results, summary = validate.validate(vault())
        failed = [r for r in results if r.errors]
        for r in failed[:30]:
            print(r.slide_id, r.errors[:2])
        print(json.dumps(summary, indent=1))
        problems = validate.floor_problems(summary)
        for problem in problems:
            print("floor:", problem)
        return 1 if failed or problems else 0
    elif args.step == "bake":
        from app.base import bake

        manifest = bake.bake(args.out, vault(), set(args.only) or None)
        print(f"{len(manifest['slides'])} slides baked, {manifest['failed_jobs']} failed jobs")
        return 1 if manifest["failed_jobs"] else 0
    elif args.step == "import":
        from app.base import importer

        print(importer.import_bake(args.bake, get_settings()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
