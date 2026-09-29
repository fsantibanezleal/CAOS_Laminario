"""The lock: every base-collection slide, fully specified, built from the curated selection.

``data/base/selection.yaml`` is what the curator writes: per collection, the records chosen after looking at them
(``python -m app.base harvest`` sheets), with the decisions a record cannot make (the anchor when the source has no
taxon field, the preparation, the part, a polarised pair). ``build`` expands it with the candidates' provenance
(URL, licence, rights holder, creator), resolves names to GBIF backbone keys (``names``) and records the lineage of
every taxon (``data/base/taxa.json``), places each slide with the tree's engine, and writes ``data/base/lock.yaml``.

The lock is committed and self-contained: acquisition, validation and the bake read only it (and the vault).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml

from app.base import names as base_names
from app.base.http import Polite
from app.base.sources import nhm
from app.collections import vocab
from app.collections.placement import place
from app.collections.rules import Facts
from app.collections.tree import load_tree

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "base"
SELECTION = DATA / "selection.yaml"
LOCK = DATA / "lock.yaml"
TAXA = DATA / "taxa.json"
GBIF = "https://api.gbif.org/v1"
ZENODO = "https://zenodo.org/api/records/"
OPENSLIDE = "https://openslide.cs.cmu.edu/download/openslide-testdata/"

DEFAULT_PREPARATION = {"rock": "thin_section", "mineral": "thin_section", "crystal": "whole_mount",
                       "material": "whole_mount", "taxon": "whole_mount"}


class LockError(ValueError):
    pass


def candidates(vault: Path) -> dict[tuple[str, str], dict]:
    out = {}
    for path in sorted((vault / "candidates").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            c = json.loads(line)
            out[(c["source"], str(c["record_id"]))] = c
    return out


def load_taxa() -> dict[str, dict]:
    return json.loads(TAXA.read_text(encoding="utf-8")) if TAXA.exists() else {}


def lineage(http: Polite, key: int, taxa: dict[str, dict]) -> dict:
    """The record and lineage of a backbone key, as the taxon cache keeps it (``app.collections.taxa``)."""
    if str(key) in taxa:
        return taxa[str(key)]
    record = http.json(f"{GBIF}/species/{key}")
    status = str(record.get("taxonomicStatus", "")).lower()
    accepted = record.get("acceptedKey") if "synonym" in status else None
    parents = http.json(f"{GBIF}/species/{accepted or key}/parents")
    taxa[str(key)] = {"key": key, "name": record.get("canonicalName") or record.get("scientificName"),
                      "rank": str(record.get("rank", "")).lower(), "status": "synonym" if accepted else status,
                      "accepted_key": accepted, "lineage": [p["key"] for p in parents],
                      "dataset": record.get("datasetKey")}
    return taxa[str(key)]


def facts_for(anchor: dict, specimen: dict, taxa: dict[str, dict]) -> Facts:
    part, preservation = specimen.get("part"), specimen.get("preservation", "recent")
    if anchor["kind"] == "taxon":
        t = taxa[anchor["ref"]]
        key = t["accepted_key"] or t["key"]
        return Facts("taxon", key=key, lineage=frozenset(t["lineage"]) | {t["key"], key}, part=part,
                     preservation=preservation)
    term = vocab.resolve_term(anchor["kind"], anchor["ref"], anchor.get("classification"))
    if isinstance(term, vocab.Problem):
        raise LockError(f"{anchor}: {term.message}")
    return Facts(anchor["kind"], path=term.path, part=part, preservation=preservation)


def _media_asset(media: dict, family: str, role: str, record: dict, **extra) -> dict:
    if not (media.get("creator") or media.get("rights_holder")):
        raise LockError("the source records no author or rights holder, so the image cannot be attributed")
    if len(str(record["record_id"])) > 200:
        raise LockError("the source's record id is longer than the contract's 200 characters")
    return {"family": family, "role": role, "url": media["url"], "record_id": str(record["record_id"]),
            "record_url": record["record_url"], "licence": media["licence"],
            "rights_holder": media.get("rights_holder"), "creator": media.get("creator"),
            "width": media.get("width"), "height": media.get("height"), **{k: v for k, v in extra.items() if v}}


def _anchor(http: Polite, pick: dict, record: dict | None, names: dict, taxa: dict) -> dict:
    if "taxon" in pick:
        resolved = base_names.resolve(http, pick["taxon"], names)
        lineage(http, resolved["key"], taxa)
        return {"kind": "taxon", "ref": str(resolved["key"]), "name": pick.get("name") or resolved["name"],
                "rank": resolved["rank"]}
    if record is not None and record["source"] == "nhm" and "anchor" not in pick:
        occ = nhm.occurrence_taxon(http, record["hints"]["gbifID"])
        key = occ["acceptedTaxonKey"] or occ["taxonKey"]
        t = lineage(http, key, taxa)
        return {"kind": "taxon", "ref": str(key), "name": occ["acceptedScientificName"] or t["name"],
                "rank": (occ.get("taxonRank") or t["rank"]).lower()}
    for kind in ("rock", "mineral", "crystal", "material"):
        if kind in pick:
            term = vocab.resolve_term(kind, pick[kind], pick.get("classification"))
            if isinstance(term, vocab.Problem):
                raise LockError(f"{pick}: {term.message}; expected {term.expected}")
            anchor = {"kind": kind, "ref": term.ref, "name": pick.get("name") or pick[kind]}
            if term.rank:
                anchor["rank"] = term.rank
            if term.classification:
                anchor["classification"] = term.classification
            return anchor
    raise LockError(f"{pick}: no anchor")


def _assets(pick: dict, record: dict | None, cands: dict) -> list[dict]:
    modality = pick.get("modality", "brightfield")
    if "pair" in pick:
        out = []
        for state, title in (("ppl", pick["pair"]["ppl"]), ("xpl", pick["pair"]["xpl"])):
            c = cands.get(("commons", title))
            if c is None:
                raise LockError(f"{title} is not among the harvested candidates")
            out.append(_media_asset(c["media"][0], "micro", "polarised", c, modality=f"polarised_{state}",
                                    polarisation={"state": state, "angle_deg": 0}, caption=pick.get("caption")))
        return out
    if record is None:
        raise LockError(f"{pick}: no record")
    if record["source"] == "commons":
        return [_media_asset(record["media"][0], "micro", "single", record, modality=modality,
                             pixel_size_um=pick.get("pixel_size_um"), caption=pick.get("caption"))]
    if record["source"] == "nhm":
        chosen = pick.get("media") or [m["media_id"] for m in record["media"] if m["role_hint"] in ("macro", "micro")]
        out = []
        for m in record["media"]:
            if m["media_id"] not in chosen:
                continue
            if m["role_hint"] == "macro":
                out.append(_media_asset(m, "macro", "slide_overview", record, caption="The slide with its labels"))
            else:
                out.append(_media_asset(m, "micro", "single", record, modality=modality,
                                        caption=pick.get("caption")))
        return out
    raise LockError(f"{record['source']}: not an image source")


def _wsi(pick: dict, http: Polite) -> tuple[dict, list[dict]]:
    """A whole-slide image from Zenodo or the OpenSlide corpus: its record and its one asset."""
    if "zenodo" in pick:
        rec = http.json(f"{ZENODO}{pick['zenodo']['record']}")
        f = next(x for x in rec["files"] if x["key"] == pick["zenodo"]["file"])
        licence = "https://creativecommons.org/licenses/by/4.0/" if rec["metadata"]["license"]["id"] == "cc-by-4.0" \
            else None
        record = {"source": "zenodo", "record_id": f"zenodo:{pick['zenodo']['record']}/{f['key']}",
                  "record_url": rec["links"]["self_html"] if "self_html" in rec["links"] else rec["doi_url"]}
        media = {"url": f["links"]["self"], "licence": licence, "rights_holder": None,
                 "creator": "; ".join(c["name"] for c in rec["metadata"].get("creators", [])),
                 "md5": f["checksum"].removeprefix("md5:"), "bytes": f["size"]}
    else:
        path = pick["openslide"]
        index = http.json(OPENSLIDE + "index.json")
        entry = index[path]
        licence = "https://creativecommons.org/publicdomain/zero/1.0/" if entry["license"] == "CC0-1.0" else None
        record = {"source": "openslide", "record_id": f"openslide:{path}", "record_url": OPENSLIDE + path}
        media = {"url": OPENSLIDE + path, "licence": licence, "rights_holder": None,
                 "creator": "OpenSlide test data (Carnegie Mellon University)", "sha256": entry.get("sha256"),
                 "bytes": entry.get("size")}
    if not media["licence"]:
        raise LockError(f"{record['record_id']}: no licence of the base policy")
    stack = pick.get("stack", False)
    asset = {"family": "micro", "role": "z_plane" if stack else "pyramid", "url": media["url"],
             "record_id": record["record_id"], "record_url": record["record_url"], "licence": media["licence"],
             "rights_holder": media["rights_holder"], "creator": media["creator"],
             "modality": pick.get("modality", "brightfield"), "wsi": True,
             **({"stack": "policy"} if stack else {}),
             **{k: media[k] for k in ("md5", "sha256", "bytes") if media.get(k)}}
    return record, [asset]


def build(vault: Path) -> dict:
    """Expand the selection into the lock; every pick that does not build is reported, none is skipped."""
    selection = yaml.safe_load(SELECTION.read_text(encoding="utf-8"))
    cands = candidates(vault)
    names = base_names.load()
    taxa = load_taxa()
    tree = load_tree()
    slides: list[dict] = []
    seen: set[str] = set()
    failures: list[str] = []
    with Polite(pause_s=0.3) as http:
        for collection, picks in selection.items():
            for pick in picks:
                try:
                    slides.append(_one(http, collection, pick, cands, names, taxa, tree, seen))
                except (LockError, base_names.NameError_, KeyError, StopIteration) as exc:
                    label = pick.get("commons") or pick.get("nhm") or pick.get("pair") or pick
                    failures.append(f"{collection}: {label}: {exc}")
    base_names.save(names)
    TAXA.write_text(json.dumps(dict(sorted(taxa.items(), key=lambda kv: int(kv[0]))), indent=1,
                               ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if failures:
        raise LockError(f"{len(failures)} picks do not build:\n" + "\n".join(failures))
    lock = {"about": "The base collection, generated by python -m app.base lock from data/base/selection.yaml; "
                     "do not edit by hand.", "built_on": date.today().isoformat(), "slides": slides}
    LOCK.write_text(yaml.safe_dump(lock, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8",
                    newline="\n")
    return lock


def _one(http: Polite, collection: str, pick: dict, cands: dict, names: dict, taxa: dict, tree,
         seen: set[str]) -> dict:
    """One lock slide from one pick."""
    record = None
    if "zenodo" in pick or "openslide" in pick:
        record, assets = _wsi(pick, http)
    else:
        ref = ("commons", pick["commons"]) if "commons" in pick else \
            ("nhm", str(pick["nhm"])) if "nhm" in pick else None
        if ref is not None:
            record = cands.get(ref)
            if record is None:
                raise LockError(f"{ref} is not among the harvested candidates")
        assets = _assets(pick, record, cands)
    if "pair" in pick:
        record = cands[("commons", pick["pair"]["xpl"])]
    anchor = _anchor(http, pick, record, names, taxa)
    specimen = {"anchor": anchor}
    for field in ("part", "preservation", "collected_on", "collector", "locality_text", "type_status"):
        if pick.get(field):
            specimen[field] = pick[field]
    if record and record["source"] == "nhm":
        hints = record["hints"]
        if hints.get("country") and "locality_text" not in specimen:
            specimen["locality_text"] = hints["country"]
        if hints.get("typeStatus") and "type_status" not in specimen:
            specimen["type_status"] = str(hints["typeStatus"]).split()[0].lower()
    if pick.get("host"):
        resolved = base_names.resolve(http, pick["host"], names)
        lineage(http, resolved["key"], taxa)
        specimen["host"] = {"kind": "taxon", "ref": str(resolved["key"]), "name": resolved["name"],
                            "rank": resolved["rank"]}
    facts = facts_for(anchor, specimen, taxa)
    placed = place(facts, tree)
    node = pick.get("node") or placed.suggestion
    if node is None or node not in placed.accepting:
        raise LockError(f"{node} does not take it; suggested {placed.suggestion}")
    slide_id = pick.get("id") or _slide_id(collection, record, pick)
    if slide_id in seen:
        raise LockError(f"duplicate slide id {slide_id}")
    seen.add(slide_id)
    photographed = record is not None and record["source"] in ("nhm",)
    slide = {
        "format": pick.get("format", "iso_76x26"),
        "format_assumed": not photographed and "format" not in pick,
        "preparation": pick.get("prep") or DEFAULT_PREPARATION[anchor["kind"]],
    }
    for field in ("stain", "mountant", "coverslip", "preparer"):
        if pick.get(field):
            slide[field] = pick[field]
    if record and record["source"] == "nhm":
        slide["catalogue_number"] = str(record["record_id"])
    if pick.get("catalogue_number"):
        slide["catalogue_number"] = pick["catalogue_number"]
    return {"id": slide_id, "collection": collection, "slide": slide, "specimen": specimen,
            "placement": {"node": node}, "assets": assets, "note": pick.get("note", "")}


def _slide_id(collection: str, record: dict | None, pick: dict) -> str:
    import hashlib
    import re

    basis = str(record["record_id"]) if record else json.dumps(pick, sort_keys=True)
    stem = re.sub(r"[^a-z0-9]+", "-", basis.lower().removeprefix("file:"))[:40].strip("-")
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:6]
    return f"{collection.split('.')[-1]}-{stem}-{digest}"
