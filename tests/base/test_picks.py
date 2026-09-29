"""The curator's picks notation (``app.base.picks``): every head form, anchor form and extra."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.base.picks import parse


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    folder = tmp_path / "candidates"
    folder.mkdir()
    rows = ["n\tsource\trecord\ttitle\tlicence\tsize\thints",
            "1\tcommons\tFile:A.jpg\tA\tcc0\t1000x1000\t",
            "2\tcommons\tFile:B ppl.jpg\tB\tcc0\t1000x1000\t",
            "3\tcommons\tFile:B xpl.jpg\tB\tcc0\t1000x1000\t"]
    (folder / "earth.rocks.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return tmp_path


def test_sheet_pick_with_every_field(vault: Path):
    text = ("[earth.rocks]\n"
            "earth.rocks 1 | rock=granite | thin_section | | polarised_xpl | | earth.rocks.igneous | a note | "
            "locality=Somewhere; collected=1990-08-10; name=Granit; pixel=1.5\n")
    pick = parse(text, vault)["earth.rocks"][0]
    assert pick == {"commons": "File:A.jpg", "rock": "granite", "prep": "thin_section", "modality": "polarised_xpl",
                    "node": "earth.rocks.igneous", "note": "a note", "locality_text": "Somewhere",
                    "collected_on": "1990-08-10", "name": "Granit", "pixel_size_um": 1.5}


def test_pair_and_fossil_default(vault: Path):
    parsed = parse("[earth.rocks]\npair earth.rocks 2 3 | rock=basalt | thin_section\n"
                   "[earth.fossils]\nnhm NHMUK1 | taxon=Ostracoda@class\n"
                   "nhm NHMUK2 | taxon=Ostracoda@class~recent\n", vault)
    assert parsed["earth.rocks"][0]["pair"] == {"ppl": "File:B ppl.jpg", "xpl": "File:B xpl.jpg"}
    fossils = parsed["earth.fossils"]
    assert fossils[0]["preservation"] == "fossil"
    assert fossils[1]["preservation"] == "recent"


def test_whole_slide_heads_and_stack(vault: Path):
    parsed = parse("[life.insects]\n"
                   "zenodo 18461326 12_Tetraleurodes 2024-01-04 11.10.43.ndpi | taxon=Tetraleurodes@genus | "
                   "whole_mount | | | | | | stack=policy; type=holotype; catalogue=USNM 1\n"
                   "openslide Philips-TIFF/Philips-1.tiff | taxon=Homo sapiens@species\n", vault)
    zenodo, openslide = parsed["life.insects"]
    assert zenodo["zenodo"] == {"record": "18461326", "file": "12_Tetraleurodes 2024-01-04 11.10.43.ndpi"}
    assert zenodo["stack"] == "policy" and zenodo["type_status"] == "holotype"
    assert zenodo["catalogue_number"] == "USNM 1"
    assert openslide["openslide"] == "Philips-TIFF/Philips-1.tiff"


def test_crystal_and_mineral_classifications(vault: Path):
    parsed = parse("[matter.crystals]\nearth.rocks 1 | crystal=ice/hexagonal:CP\n"
                   "[earth.minerals]\nearth.rocks 1 | mineral=Quartz:4.DA\n", vault)
    assert parsed["matter.crystals"][0]["crystal"] == "ice/hexagonal"
    assert parsed["matter.crystals"][0]["classification"] == "CP"
    assert parsed["earth.minerals"][0] == {"commons": "File:A.jpg", "mineral": "Quartz", "classification": "4.DA"}


def test_a_stack_other_than_the_policy_is_refused(vault: Path):
    with pytest.raises(ValueError, match="stack takes only"):
        parse("[life.insects]\nearth.rocks 1 | taxon=Diptera@order | | | | | | | stack=all\n", vault)
