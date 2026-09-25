from app.contracts import licences

CANONICAL_CASES = {
    "http://creativecommons.org/licenses/by/4.0": "https://creativecommons.org/licenses/by/4.0/",
    "https://creativecommons.org/licenses/by/4.0/legalcode": "https://creativecommons.org/licenses/by/4.0/",
    "https://creativecommons.org/licenses/by-sa/3.0/deed.en": "https://creativecommons.org/licenses/by-sa/3.0/",
    "https://creativecommons.org/licenses/by-sa/3.0/de/": "https://creativecommons.org/licenses/by-sa/3.0/de/",
    "https://creativecommons.org/publicdomain/zero/1.0/": licences.CC0,
    "http://creativecommons.org/publicdomain/mark/1.0/deed.en": licences.PDM,
    "http://rightsstatements.org/vocab/NKC/1.0/": licences.NKC,
    "https://creativecommons.org/licenses/by-nc/4.0/": "https://creativecommons.org/licenses/by-nc/4.0/",
}


def test_policy_sets_and_normalisation():
    for spelled, canon in CANONICAL_CASES.items():
        assert licences.canonical(spelled) == canon, spelled
    assert licences.canonical("all rights reserved") is None
    assert licences.canonical("https://creativecommons.org/licenses/by-nd/4.0/") is not None

    base_ok = ["https://creativecommons.org/licenses/by/2.0/", "https://creativecommons.org/licenses/by-sa/3.0/de/",
               licences.CC0, licences.PDM, licences.NKC]
    for uri in base_ok:
        assert licences.allowed(uri, "base"), uri
        assert licences.allowed(uri, "contribution"), uri
    nc = "https://creativecommons.org/licenses/by-nc/4.0/"
    nc_sa = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
    assert not licences.allowed(nc, "base") and licences.allowed(nc, "contribution")
    assert not licences.allowed(nc_sa, "base") and licences.allowed(nc_sa, "contribution")
    for refused in ["https://creativecommons.org/licenses/by-nd/4.0/",
                    "https://creativecommons.org/licenses/by-nc-nd/4.0/",
                    "https://creativecommons.org/licenses/by-nc/3.0/",
                    "https://creativecommons.org/licenses/by/1.0/", "proprietary"]:
        assert not licences.allowed(refused, "contribution"), refused


def test_short_names():
    assert licences.short_name("https://creativecommons.org/licenses/by-sa/3.0/de/") == "CC BY-SA 3.0 DE"
    assert licences.short_name(licences.CC0) == "CC0 1.0"
    assert licences.short_name("https://creativecommons.org/licenses/by/4.0/") == "CC BY 4.0"
