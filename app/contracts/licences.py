"""The licence policy: which licences an asset may carry, as canonical URIs.

Sources spell the same licence many ways (``http://creativecommons.org/licenses/by/4.0``,
``https://creativecommons.org/licenses/by/4.0/legalcode``, ``.../deed.en``). ``canonical()`` reduces them to
one form: https, the licence path, a trailing slash, jurisdiction ports kept.

The base collection accepts only licences that allow reuse without restriction on purpose: CC0, the public
domain mark, the no-known-copyright statement, CC BY and CC BY-SA. Contributions may also choose the
non-commercial variants, as on iNaturalist.
"""

from __future__ import annotations

import re
from typing import Literal

Origin = Literal["base", "contribution"]

CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
PDM = "https://creativecommons.org/publicdomain/mark/1.0/"
NKC = "https://rightsstatements.org/vocab/NKC/1.0/"

_CC_LICENCE = re.compile(
    r"^(?:https?://)?(?:www\.)?creativecommons\.org/licenses/"
    r"(?P<family>by|by-sa|by-nc|by-nc-sa|by-nd|by-nc-nd)/(?P<version>\d\.\d)"
    r"(?:/(?P<port>[a-z]{2}(?:-[a-z]{2})?))?"
    r"(?:/(?:legalcode(?:\.[a-z-]+)?|deed(?:\.[a-z-]+)?))?/?$",
    re.IGNORECASE,
)
_CC_PUBLIC = re.compile(
    r"^(?:https?://)?(?:www\.)?creativecommons\.org/publicdomain/(?P<kind>zero|mark)/1\.0"
    r"(?:/(?:legalcode(?:\.[a-z-]+)?|deed(?:\.[a-z-]+)?))?/?$",
    re.IGNORECASE,
)
_RIGHTS = re.compile(r"^(?:https?://)?rightsstatements\.org/(?:vocab|page)/NKC/1\.0/?$", re.IGNORECASE)

#: Versions accepted for the attribution families in the base collection.
_BASE_VERSIONS = {"2.0", "2.5", "3.0", "4.0"}

SHORT_NAMES = {CC0: "CC0 1.0", PDM: "Public Domain Mark 1.0", NKC: "No Known Copyright"}


def canonical(uri: str) -> str | None:
    """The canonical form of a licence URI, or ``None`` when it is not a licence this policy recognises."""
    text = uri.strip()
    m = _CC_PUBLIC.match(text)
    if m:
        return CC0 if m["kind"].lower() == "zero" else PDM
    if _RIGHTS.match(text):
        return NKC
    m = _CC_LICENCE.match(text)
    if m:
        port = f"{m['port'].lower()}/" if m["port"] else ""
        return f"https://creativecommons.org/licenses/{m['family'].lower()}/{m['version']}/{port}"
    return None


def short_name(uri: str) -> str:
    """A human label such as ``CC BY-SA 3.0 DE`` for a canonical URI."""
    if uri in SHORT_NAMES:
        return SHORT_NAMES[uri]
    m = _CC_LICENCE.match(uri)
    if not m:
        return uri
    port = f" {m['port'].upper()}" if m["port"] else ""
    return f"CC {m['family'].upper()} {m['version']}{port}"


def allowed(uri: str, origin: Origin) -> bool:
    """Whether a licence is accepted for an asset of the given origin."""
    canon = canonical(uri)
    if canon is None:
        return False
    if canon in (CC0, PDM, NKC):
        return True
    m = _CC_LICENCE.match(canon)
    family, version, port = m["family"].lower(), m["version"], m["port"]
    if family in ("by", "by-sa") and version in _BASE_VERSIONS:
        return True
    if origin == "contribution" and family in ("by-nc", "by-nc-sa") and version == "4.0" and not port:
        return True
    return False


def expectation(origin: Origin) -> str:
    base = "CC0, Public Domain Mark, No Known Copyright, CC BY or CC BY-SA 2.0 to 4.0"
    if origin == "contribution":
        return base + ", CC BY-NC 4.0 or CC BY-NC-SA 4.0"
    return base
