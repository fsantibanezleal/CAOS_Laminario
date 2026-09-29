"""The remote-asset contract: another institution's IIIF image service used as a slide's image.

Remote services are referenced, not mirrored (a non-goal of the design). One is accepted only when:

1. **availability**: its ``info.json`` answers HTTP 200 with JSON;
2. **protocol**: it declares IIIF Image API 2 or 3 in its ``@context``;
3. **rights**: it declares a licence (``rights`` in version 3, ``license`` in version 2) that the licence policy
   accepts for the slide's origin;
4. **cors**: it lets a browser on this deployment read it (``Access-Control-Allow-Origin`` is ``*`` or this
   origin), since OpenSeadragon fetches it from the page;
5. **dimensions**: its width and height equal the ones recorded for the asset.

Every failure names its field and what was expected, as the ingestion contract's errors do. The same check
runs at import and in the link-check command (``scripts/check_remote_iiif.py``), which re-reads every remote
asset and reports differences without changing anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx2

from app.contracts import licences

TIMEOUT_SECONDS = 20.0
USER_AGENT = "Laminario remote-asset check (https://github.com/fsantibanezleal/CAOS_Laminario)"


@dataclass(frozen=True)
class Problem:
    field: str
    message: str
    expected: str


@dataclass
class RemoteCheck:
    info_url: str
    version: int | None = None
    width: int | None = None
    height: int | None = None
    licence_uri: str | None = None
    problems: list[Problem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _version(document: dict) -> int | None:
    context = document.get("@context")
    contexts = context if isinstance(context, list) else [context]
    for item in contexts:
        if isinstance(item, str) and "iiif.io/api/image/3" in item:
            return 3
        if isinstance(item, str) and "iiif.io/api/image/2" in item:
            return 2
    return None


def _declared_licence(document: dict, version: int | None) -> str | None:
    value = document.get("rights") if version == 3 else document.get("license")
    if isinstance(value, list):
        value = next((v for v in value if isinstance(v, str)), None)
    return value if isinstance(value, str) else None


def check_remote_asset(info_url: str, *, width: int, height: int, origin: licences.Origin,
                       request_origin: str, client: httpx2.Client | None = None) -> RemoteCheck:
    """Apply the remote-asset contract to one ``info.json`` URL."""
    result = RemoteCheck(info_url=info_url)
    own_client = client is None
    client = client or httpx2.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True)
    try:
        try:
            response = client.get(info_url, headers={"Origin": request_origin, "User-Agent": USER_AGENT,
                                                     "Accept": "application/ld+json, application/json"})
        except httpx2.HTTPError as exc:
            result.problems.append(Problem("availability", f"no answer ({type(exc).__name__})", "HTTP 200"))
            return result
    finally:
        if own_client:
            client.close()
    if response.status_code != 200:
        result.problems.append(Problem("availability", f"answered HTTP {response.status_code}", "HTTP 200"))
        return result
    try:
        document = response.json()
    except ValueError:
        result.problems.append(Problem("availability", "the answer is not JSON", "a IIIF info.json"))
        return result
    if not isinstance(document, dict):
        result.problems.append(Problem("availability", "the answer is not a JSON object", "a IIIF info.json"))
        return result

    result.version = _version(document)
    if result.version is None:
        result.problems.append(Problem("protocol", "no IIIF Image API context", "IIIF Image API 2 or 3"))

    declared = _declared_licence(document, result.version)
    if declared is None:
        result.problems.append(Problem("rights", "no licence declared", licences.expectation(origin)))
    elif not licences.allowed(declared, origin):
        result.problems.append(Problem("rights", f"{declared} is not accepted", licences.expectation(origin)))
    else:
        result.licence_uri = licences.canonical(declared)

    allow = response.headers.get("access-control-allow-origin")
    if allow not in ("*", request_origin):
        result.problems.append(Problem("cors", f"Access-Control-Allow-Origin is {allow!r}",
                                       f"'*' or {request_origin!r}"))

    w, h = document.get("width"), document.get("height")
    result.width = w if isinstance(w, int) else None
    result.height = h if isinstance(h, int) else None
    if (result.width, result.height) != (width, height):
        result.problems.append(Problem("dimensions", f"{w} x {h} px", f"{width} x {height} px as recorded"))
    return result
