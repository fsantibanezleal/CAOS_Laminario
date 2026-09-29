"""Wikimedia Commons: files of a category tree, with their licence, author and size (MediaWiki Action API).

The licence is read from each file's ``extmetadata`` (``LicenseUrl``, else ``License``/``LicenseShortName`` for the
public-domain and CC0 tags that carry no URL); a file whose licence is not in the base policy is dropped. Commons
has no taxon field: the curator reads the description and the categories, which are kept as hints.
"""

from __future__ import annotations

import html
import re
from datetime import date

from app.base.http import Polite
from app.contracts import licences

API = "https://commons.wikimedia.org/w/api.php"
PAGE = "https://commons.wikimedia.org/wiki/"
IMAGE_MIME = {"image/jpeg", "image/png", "image/tiff", "image/webp"}
#: Subcategories not walked into: electron micrographs are not light microscopy (dossier 06), videos are not images.
SKIP = re.compile(r"electron micro|videos?", re.IGNORECASE)
FIELDS = "LicenseUrl|License|LicenseShortName|Artist|Credit|ImageDescription|DateTimeOriginal|ObjectName"


def plain(markup: str | None) -> str:
    """Text of a Commons metadata field, without its HTML."""
    text = re.sub(r"<[^>]+>", " ", markup or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


# A Commons "Artist" field is written for the file page: templates add a way to contact the author, a talk link, a
# derivative's source file, an uploader's note, sometimes an email. The credit keeps the people and drops the rest.
MUSHROOM_OBSERVER = re.compile(r"^This image was created by user (?P<who>.+?) at Mushroom Observer\s*,.*$", re.S)
UPLOADED = re.compile(r"^The original uploader was (?P<up>.+?) at (?P<wiki>\S+) Wikipedia\s*\.?\s*"
                      r"\(\s*Original text:\s*(?P<orig>.+?)\s*\)\s*$")
UPLOADER_ONLY = re.compile(r"^The original uploader was (?P<up>.+?) at (?P<wiki>\S+) Wikipedia\s*\.?\s*$")
DERIVATIVE = re.compile(r"^(?:\S+\.(?:jpe?g|png|tiff?|gif|svg|webp)\s*:\s*)?(?P<orig>.+?)\s+derivative work:\s*"
                        r"(?P<by>.+)$", re.I)
EMAIL = re.compile(r"\s*\(?\s*[\w.+-]+@[\w-]+(?:\.[\w-]+)+\s*\)?")
URL = re.compile(r"\s*\(?\s*https?://\S+?\s*\)")
BARE_URL = re.compile(r"\s*https?://\S+")
TALK = re.compile(r"\s*\(\s*talk\s*\)", re.I)
COPYRIGHT = re.compile(r"^\s*(?:Copyright\s*)?©\s*\d{4}\s*", re.I)


def credit(artist: str | None) -> str | None:
    """The people a Commons file credits, without the page's furniture (``Ron Pastorino (Ronpast), Mushroom
    Observer``, not ``This image was created by user Ron Pastorino (Ronpast) at Mushroom Observer , a source for
    mycological images. You can contact this user here .``)."""
    text = re.sub(r"\s+", " ", artist or "").strip()
    if not text:
        return None
    if m := MUSHROOM_OBSERVER.match(text):
        who = COPYRIGHT.sub("", EMAIL.sub("", m["who"])).strip()
        name, _, nick = who.partition(" (")
        nick = nick.rstrip(")").strip()
        who = name.strip() if not nick or nick.lower() == name.strip().lower() else f"{name.strip()} ({nick})"
        text = f"{who}, Mushroom Observer"
    elif m := UPLOADED.match(text):
        text = f"{m['orig']} (uploaded to the {m['wiki']} Wikipedia by {m['up']})"
    elif m := UPLOADER_ONLY.match(text):
        text = f"{m['up']} (the {m['wiki']} Wikipedia)"
    text = TALK.sub("", text)
    text = URL.sub("", text)
    text = BARE_URL.sub("", text)
    text = EMAIL.sub("", text)
    if m := DERIVATIVE.match(text):
        text = f"{m['orig'].strip()}; derivative work by {m['by'].strip()}"
    text = re.sub(r"\s+([.,;:])", r"\1", re.sub(r"\s+", " ", text)).strip(" ,;:")
    return text or None


def licence_of(meta: dict) -> str | None:
    """The canonical licence URI of a file, or None when the policy does not know it."""
    url = meta.get("LicenseUrl", {}).get("value")
    if url:
        return licences.canonical(url)
    code = (meta.get("License", {}).get("value") or "").lower()
    short = (meta.get("LicenseShortName", {}).get("value") or "").lower()
    if code == "cc0" or short.startswith("cc0"):
        return licences.CC0
    if code.startswith("pd") or short == "public domain":
        return licences.PDM
    return None


def subcategories(http: Polite, category: str) -> list[str]:
    out, params = [], {"action": "query", "list": "categorymembers", "cmtitle": category, "cmtype": "subcat",
                       "cmlimit": "500", "format": "json", "maxlag": "5"}
    while True:
        data = http.json(API, params)
        out += [m["title"] for m in data.get("query", {}).get("categorymembers", [])]
        if "continue" not in data:
            return out
        params = {**params, **data["continue"]}


def files(http: Polite, category: str, thumb_px: int = 320) -> list[dict]:
    """Every file of one category with its image information and visible categories."""
    params = {"action": "query", "generator": "categorymembers", "gcmtitle": category, "gcmtype": "file",
              "gcmlimit": "100", "prop": "imageinfo|categories", "iiprop": "url|size|sha1|extmetadata|mime",
              "iiextmetadatafilter": FIELDS, "iiurlwidth": str(thumb_px), "clshow": "!hidden", "cllimit": "max",
              "format": "json", "maxlag": "5"}
    pages: dict[str, dict] = {}
    while True:
        data = http.json(API, params)
        for page in data.get("query", {}).get("pages", {}).values():
            entry = pages.setdefault(page["title"], {"title": page["title"], "categories": set()})
            if page.get("imageinfo"):
                entry["info"] = page["imageinfo"][0]
            entry["categories"].update(c["title"].removeprefix("Category:") for c in page.get("categories", []))
        if "continue" not in data:
            break
        params = {**params, **data["continue"]}
    return list(pages.values())


def named(http: Polite, titles: list[str], thumb_px: int = 320) -> list[dict]:
    """Files named one by one (a category that holds too few, or a file found by search), as ``files`` returns them."""
    out = []
    for start in range(0, len(titles), 40):
        params = {"action": "query", "titles": "|".join(titles[start:start + 40]), "prop": "imageinfo|categories",
                  "iiprop": "url|size|sha1|extmetadata|mime", "iiextmetadatafilter": FIELDS,
                  "iiurlwidth": str(thumb_px), "clshow": "!hidden", "cllimit": "max", "format": "json",
                  "maxlag": "5"}
        data = http.json(API, params)
        for page in data.get("query", {}).get("pages", {}).values():
            if page.get("imageinfo"):
                out.append({"title": page["title"], "info": page["imageinfo"][0],
                            "categories": {c["title"].removeprefix("Category:") for c in page.get("categories", [])}})
    return out


def candidate(page: dict, category: str, min_side: int) -> dict | None:
    info = page.get("info")
    if not info or info.get("mime") not in IMAGE_MIME or max(info["width"], info["height"]) < min_side:
        return None
    meta = info.get("extmetadata", {})
    licence = licence_of(meta)
    if not licence or not licences.allowed(licence, "base"):
        return None
    title = page["title"]
    return {
        "source": "commons",
        "record_id": title,
        "record_url": PAGE + title.replace(" ", "_"),
        "title": plain(meta.get("ObjectName", {}).get("value")) or title.removeprefix("File:"),
        "description": plain(meta.get("ImageDescription", {}).get("value"))[:600],
        "media": [{
            "media_id": title,
            "url": info["url"],
            "thumb": info.get("thumburl"),
            "width": info["width"],
            "height": info["height"],
            "mime": info["mime"],
            "sha1": info.get("sha1"),
            "licence": licence,
            "creator": (credit(plain(meta.get("Artist", {}).get("value"))) or "")[:200] or None,
            "rights_holder": None,
            "credit": plain(meta.get("Credit", {}).get("value"))[:300] or None,
            "date": plain(meta.get("DateTimeOriginal", {}).get("value"))[:40] or None,
        }],
        "hints": {"categories": sorted(page["categories"]), "harvested_from": category},
        "harvested_on": date.today().isoformat(),
    }


def harvest(http: Polite, root: str, depth: int = 2, min_side: int = 1000, limit: int = 400) -> tuple[list[dict], dict]:
    """Candidates from a category and its subcategories to ``depth`` levels, with counts of what was dropped."""
    seen_categories: set[str] = set()
    seen_files: set[str] = set()
    out: list[dict] = []
    counts = {"files": 0, "kept": 0, "categories": 0}
    frontier = [(root if root.startswith("Category:") else f"Category:{root}", 0)]
    while frontier and len(out) < limit:
        category, level = frontier.pop(0)
        if category in seen_categories:
            continue
        seen_categories.add(category)
        counts["categories"] += 1
        for page in files(http, category):
            if page["title"] in seen_files:
                continue
            seen_files.add(page["title"])
            counts["files"] += 1
            found = candidate(page, category, min_side)
            if found:
                out.append(found)
                if len(out) >= limit:
                    break
        if level < depth:
            frontier += [(sub, level + 1) for sub in subcategories(http, category) if not SKIP.search(sub)]
    counts["kept"] = len(out)
    return out, counts
