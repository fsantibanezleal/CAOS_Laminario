"""Picks: the curator's short notation for a reviewed candidate, expanded into ``data/base/selection.yaml``.

One line per slide, written while looking at a harvest sheet (``<collection>.png`` with ``<collection>.tsv``)::

    <sheet> <n> | <anchor> | <preparation> | <part> | <modality> | <stain> | <node> | <note> | <extras>

``<sheet>`` is the harvest collection whose sheet shows the image and ``<n>`` its number there; ``<anchor>`` is
``taxon=Name@rank``, ``rock=term``, ``mineral=Name``, ``crystal=origin[/system][:category]`` or
``material=term``, optionally followed by ``~fossil`` or ``~in_amber`` (picks under ``[earth.fossils]`` are fossil
unless marked); later fields may be empty. ``pair <sheet> <n_ppl> <n_xpl> | ...`` picks a registered PPL/XPL
pair. ``nhm <catalogue number> | ...`` picks an NHM record (anchor from its GBIF occurrence unless given).
``zenodo <record> <file name> | ...`` and ``openslide <path in the index> | ...`` pick a whole-slide image.
``<extras>`` are ``key=value`` pairs separated by ``;`` for facts read on the slide's label or the source's sheet:
``host`` (a name as in ``<anchor>``), ``locality``, ``collected`` (YYYY, YYYY-MM or YYYY-MM-DD), ``collector``,
``preparer``, ``name`` (the determination as written), ``type`` (the type status), ``catalogue`` (the holder's
catalogue number), ``stack`` (``policy``: a focal stack whose planes the ingest policy selects), ``pixel`` (the
pixel size in micrometres, when the source states it).
Lines starting with ``#`` are comments; the target collection of each pick is the section header
``[collection]``.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def _index(vault: Path, sheet: str) -> dict[int, tuple[str, str]]:
    """Sheet number to (source, record id), from the sheet's ``.tsv``."""
    rows = (vault / "candidates" / f"{sheet}.tsv").read_text(encoding="utf-8").splitlines()[1:]
    return {int(r.split("\t")[0]): (r.split("\t")[1], r.split("\t")[2]) for r in rows if r.strip()}


def _anchor(text: str) -> dict:
    text, _, preservation = text.partition("~")
    if preservation.strip():
        return {**_anchor(text), "preservation": preservation.strip()}
    kind, _, value = text.strip().partition("=")
    if kind == "crystal" and ":" in value:
        value, _, category = value.partition(":")
        return {"crystal": value, "classification": category}
    if kind == "mineral" and ":" in value:
        value, _, klass = value.partition(":")
        return {"mineral": value, "classification": klass}
    return {kind: value} if kind else {}


def parse(text: str, vault: Path) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    section = None
    indexes: dict[str, dict[int, str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            out.setdefault(section, [])
            continue
        fields = [f.strip() for f in line.split("|")] + [""] * 9
        head, anchor, prep, part, modality, stain, node, note, extras = fields[:9]
        words = head.split()
        pick: dict = {}
        if words[0] == "pair":
            sheet = words[1]
            idx = indexes.setdefault(sheet, _index(vault, sheet))
            pick["pair"] = {"ppl": idx[int(words[2])][1], "xpl": idx[int(words[3])][1]}
        elif words[0] == "nhm":
            pick["nhm"] = words[1]
        elif words[0] == "zenodo":
            pick["zenodo"] = {"record": words[1], "file": " ".join(words[2:])}
        elif words[0] == "openslide":
            pick["openslide"] = words[1]
        else:
            sheet, n = words[0], int(words[1])
            idx = indexes.setdefault(sheet, _index(vault, sheet))
            source, record = idx[n]
            pick[source] = record
        pick.update(_anchor(anchor))
        if section == "earth.fossils" and "preservation" not in pick:
            pick["preservation"] = "fossil"
        for key, value in (("prep", prep), ("part", part), ("modality", modality), ("stain", stain),
                           ("node", node), ("note", note)):
            if value:
                pick[key] = value
        names = {"host": "host", "locality": "locality_text", "collected": "collected_on", "collector": "collector",
                 "preparer": "preparer", "name": "name", "type": "type_status", "catalogue": "catalogue_number",
                 "stack": "stack", "pixel": "pixel_size_um"}
        for item in filter(None, (x.strip() for x in extras.split(";"))):
            key, _, value = item.partition("=")
            pick[names[key.strip()]] = value.strip()
        if "pixel_size_um" in pick:
            pick["pixel_size_um"] = float(pick["pixel_size_um"])
        if pick.get("stack") not in (None, "policy"):
            raise ValueError(f"{line}: stack takes only 'policy'")
        out[section].append(pick)
    return out


def write_selection(picks_dir: Path, vault: Path, target: Path) -> dict:
    selection: dict[str, list[dict]] = {}
    for path in sorted(picks_dir.glob("*.txt")):
        for section, items in parse(path.read_text(encoding="utf-8"), vault).items():
            selection.setdefault(section, []).extend(items)
    header = ("# The base collection's curated selection, generated from data/base/picks/*.txt by\n"
              "# python -m app.base select; each pick was chosen by looking at its image on a harvest sheet.\n")
    target.write_text(header + yaml.safe_dump(selection, sort_keys=False, allow_unicode=True, width=120),
                      encoding="utf-8", newline="\n")
    return selection
