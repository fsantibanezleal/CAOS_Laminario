"""Acquisition: every image of the lock downloaded once into the vault, with its SHA-256 and retrieval date.

Files land in ``<vault>/base/sources/<sha256>.<ext>`` (content-addressed, so a changed source is a new file, never
an overwrite). ``data/base/acquired.json`` maps each source URL to what was retrieved; it is committed, because the
SHA-256 and the date are the provenance the contract requires (R-071). A checksum the source publishes (Zenodo's
MD5, the OpenSlide index's SHA-256) is verified; a mismatch stops the step. A DICOM archive is unpacked next to its
file, since OpenSlide opens DICOM from a folder of instances.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import zipfile
from datetime import date
from pathlib import Path

import yaml

from app.base.http import USER_AGENT, SourceError
from app.base.lock import DATA, LOCK

ACQUIRED = DATA / "acquired.json"
CHUNK = 4 * 1024 * 1024


def load() -> dict[str, dict]:
    return json.loads(ACQUIRED.read_text(encoding="utf-8")) if ACQUIRED.exists() else {}


def save(acquired: dict[str, dict]) -> None:
    ACQUIRED.write_text(json.dumps(dict(sorted(acquired.items())), indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")


def _extension(url: str, content_type: str | None) -> str:
    name = url.rsplit("/", 1)[-1].split("?")[0]
    if "." in name and len(name.rsplit(".", 1)[1]) <= 5:
        return name.rsplit(".", 1)[1].lower()
    guessed = mimetypes.guess_extension((content_type or "").split(";")[0].strip()) or ".bin"
    return guessed.lstrip(".").replace("jpe", "jpg")


#: Seconds between downloads, and the first wait after a 429 or 503 (doubled each time, or the server's
#: Retry-After). Wikimedia's image servers answer 429 to clients that do not pace themselves.
PAUSE_S = 1.5
BACKOFF_S = 10.0


def download(url: str, folder: Path, attempts: int = 6) -> dict:
    """Stream a URL into ``folder``, returning its SHA-256, MD5, size and the file's name."""
    import time

    import httpx2

    folder.mkdir(parents=True, exist_ok=True)
    partial = folder / ".partial"
    last_error = None
    wait = BACKOFF_S
    for _ in range(attempts):
        time.sleep(PAUSE_S)
        sha, md5, size = hashlib.sha256(), hashlib.md5(usedforsecurity=False), 0
        try:
            with httpx2.Client(timeout=120.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
                with client.stream("GET", url) as response:
                    if response.status_code in (429, 503):
                        retry = response.headers.get("retry-after", "")
                        wait = max(wait, float(retry)) if retry.isdigit() else wait
                        raise SourceError(f"{url} answered {response.status_code}")
                    if response.status_code != 200:
                        raise SourceError(f"{url} answered {response.status_code}")
                    content_type = response.headers.get("content-type")
                    with partial.open("wb") as out:
                        for chunk in response.iter_bytes(CHUNK):
                            out.write(chunk)
                            sha.update(chunk)
                            md5.update(chunk)
                            size += len(chunk)
            digest = sha.hexdigest()
            target = folder / f"{digest}.{_extension(url, content_type)}"
            if target.exists():
                partial.unlink()
            else:
                partial.replace(target)
            return {"sha256": digest, "md5": md5.hexdigest(), "bytes": size, "file": target.name,
                    "content_type": content_type}
        except (httpx2.HTTPError, SourceError) as exc:
            last_error = exc
            time.sleep(wait)
            wait *= 2
    partial.unlink(missing_ok=True)
    raise SourceError(f"{url}: {last_error}")


def unpack_dicom(archive: Path) -> str:
    """Unpack a DICOM WSI archive beside it (no absolute or parent paths); the first instance opens the series."""
    target = archive.with_suffix("")
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        for name in names:
            if name.startswith(("/", "\\")) or ".." in Path(name).parts:
                raise SourceError(f"{archive.name}: unsafe member {name}")
        z.extractall(target)
    instances = sorted(p for p in target.rglob("*") if p.is_file() and p.suffix.lower() in (".dcm", ""))
    if not instances:
        raise SourceError(f"{archive.name}: no DICOM instance inside")
    return str(instances[0].relative_to(archive.parent)).replace("\\", "/")


def acquire(vault: Path, only: set[str] | None = None) -> dict[str, dict]:
    lock = yaml.safe_load(LOCK.read_text(encoding="utf-8"))
    acquired = load()
    folder = vault / "sources"
    for slide in lock["slides"]:
        if only and slide["id"] not in only and slide["collection"] not in only:
            continue
        for asset in slide["assets"]:
            url = asset["url"]
            known = acquired.get(url)
            if known and (folder / known["file"]).exists():
                continue
            got = download(url, folder)
            if asset.get("md5") and got["md5"] != asset["md5"]:
                raise SourceError(f"{url}: MD5 {got['md5']} differs from the record's {asset['md5']}")
            if asset.get("sha256") and got["sha256"] != asset["sha256"]:
                raise SourceError(f"{url}: SHA-256 differs from the index's")
            entry = {"sha256": got["sha256"], "bytes": got["bytes"], "file": got["file"],
                     "retrieved_on": date.today().isoformat()}
            if url.endswith(".zip"):
                entry["open"] = unpack_dicom(folder / got["file"])
            acquired[url] = entry
            save(acquired)
            print(f"{slide['id']}: {got['bytes']:,} bytes {got['sha256'][:12]}", flush=True)
    return acquired
