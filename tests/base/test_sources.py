"""The source adapters turn what a source answers into candidates, keeping only licences of the base policy."""

from __future__ import annotations

from app.base.sources import commons, nhm, smithsonian
from app.contracts import licences


def _commons_page(licence_url: str | None, short: str = "", width: int = 2000) -> dict:
    meta = {"LicenseShortName": {"value": short}, "Artist": {"value": "<a href='x'>A. Person</a>"},
            "ImageDescription": {"value": "<p>Olivine &amp; pyroxene</p>"}}
    if licence_url:
        meta["LicenseUrl"] = {"value": licence_url}
    return {"title": "File:Thin section.jpg", "categories": {"Rocks"},
            "info": {"url": "https://upload.wikimedia.org/x.jpg", "thumburl": "https://upload.wikimedia.org/t.jpg",
                     "width": width, "height": 600, "mime": "image/jpeg", "sha1": "ab", "extmetadata": meta}}


def test_commons_keeps_only_the_base_policy_and_the_size():
    kept = commons.candidate(_commons_page("https://creativecommons.org/licenses/by-sa/4.0/"), "Rocks", 1000)
    assert kept is not None
    assert kept["media"][0]["creator"] == "A. Person"
    assert kept["description"] == "Olivine & pyroxene"
    assert commons.candidate(_commons_page("https://creativecommons.org/licenses/by-nc/4.0/"), "Rocks", 1000) is None
    by = "https://creativecommons.org/licenses/by/4.0/"

    def licence(short: str) -> str | None:
        found = commons.candidate(_commons_page(None, short=short), "Rocks", 1000)
        return found and found["media"][0]["licence"]

    assert licence("CC0") == licences.CC0
    assert licence("Public domain") == licences.PDM
    assert licence("GFDL") is None
    assert commons.candidate(_commons_page(by, width=900), "Rocks", 1000) is None


def test_nhm_image_roles():
    assert nhm.image_role("010155449_1_1") == "macro"
    assert nhm.image_role("010155449__2019-11-05-Image Export-02") == "micro"
    assert nhm.image_role("010155449__2019-11-05-Scene-1-ScanRegion0") == "micro"
    assert nhm.image_role("Zoology Accessions Register: page 241") == "other"


def _si_row(access: str = "CC0") -> dict:
    return {"id": "ld1", "title": "Wilson Bentley Photomicrograph of Granular Snowflake No. 807", "unitCode": "SIA",
            "content": {"descriptiveNonRepeating": {
                "record_ID": "siris_arc_403542", "data_source": "Smithsonian Institution Archives",
                "online_media": {"media": [{"type": "Images", "idsId": "SIA-SIA2013-09153",
                                            "usage": {"access": access}}]}},
                "freetext": {"name": [{"label": "Creator", "content": "Bentley, Wilson Alwyn 1865-1931"}],
                             "notes": [{"label": "Notes", "content": "Bentley No. 807"}]}}}


def test_smithsonian_candidate_from_a_record():
    c = smithsonian.candidate(_si_row())
    assert c["source"] == "smithsonian" and c["record_id"] == "siris_arc_403542"
    assert c["record_url"] == "https://collections.si.edu/search/detail/edanmdm:siris_arc_403542"
    m = c["media"][0]
    assert m["url"] == "https://ids.si.edu/ids/deliveryService?id=SIA-SIA2013-09153"
    assert m["licence"] == licences.CC0 and licences.allowed(m["licence"], "base")
    assert m["creator"].startswith("Bentley") and m["rights_holder"] == "Smithsonian Institution Archives"
    assert smithsonian.candidate(_si_row(access="Usage conditions apply")) is None


def test_a_commons_credit_keeps_the_people_and_drops_the_page():
    from app.base.sources.commons import credit

    cases = {
        "This image was created by user Ron Pastorino (Ronpast) at Mushroom Observer , a source for mycological "
        "images. You can contact this user here .": "Ron Pastorino (Ronpast), Mushroom Observer",
        "This image was created by user Alan Rockefeller (Alan Rockefeller) at Mushroom Observer , a source for "
        "mycological images. You can contact this user here .": "Alan Rockefeller, Mushroom Observer",
        "This image was created by user Bryce Kendrick (bryce@mycolog.comj) at Mushroom Observer , a source for "
        "mycological images. You can contact this user here .": "Bryce Kendrick, Mushroom Observer",
        "This image was created by user Copyright ©2012 Byrain at Mushroom Observer , a source for mycological "
        "images. You can contact this user here .": "Byrain, Mushroom Observer",
        "This image was created by user Michael W (michael w) at Mushroom Observer , a source for mycological "
        "images. You can contact this user here .": "Michael W, Mushroom Observer",
        "Bob Blaylock ( talk )": "Bob Blaylock",
        "20100905_211652_Spirochetes.jpg : Bob Blaylock derivative work: F. Lamiot ( talk )":
            "Bob Blaylock; derivative work by F. Lamiot",
        "Traquea_avestruz.JPG : Lycaon.cl derivative work: Osado ( talk )": "Lycaon.cl; derivative work by Osado",
        "Julien Leuthold (ETH Zürich, Switzerland) ( https://imaggeo.egu.eu/user/Julien.Leuthold/ )":
            "Julien Leuthold (ETH Zürich, Switzerland)",
        "The original uploader was AndiHolz at German Wikipedia . ( Original text: A.G. Heiss, Innsbruck )":
            "A.G. Heiss, Innsbruck (uploaded to the German Wikipedia by AndiHolz)",
        "The original uploader was Tillman at English Wikipedia .": "Tillman (the English Wikipedia)",
        "Strekeisen": "Strekeisen",
        "Dr. phil.nat Thomas Geier, Fachgebiet Botanik der Forschungsanstalt Geisenheim.":
            "Dr. phil.nat Thomas Geier, Fachgebiet Botanik der Forschungsanstalt Geisenheim.",
        "": None,
    }
    for raw, expected in cases.items():
        assert credit(raw) == expected, raw


def test_an_openslide_sample_credits_its_author():
    from app.base.lock import openslide_credit

    assert openslide_credit({"credit": "Computational Pathology Group, Radboud University Medical Center"}) == \
        "Computational Pathology Group, Radboud University Medical Center"
    assert openslide_credit({"credit": "Maki Sakuma, National Center For Global Health and Medicine, DOI: "
                                       "10.5061/dryad.6m905qfzx"}) == \
        "Maki Sakuma, National Center For Global Health and Medicine (doi:10.5061/dryad.6m905qfzx)"
    assert openslide_credit({"credit": None}) == "Carnegie Mellon University (OpenSlide test data)"
