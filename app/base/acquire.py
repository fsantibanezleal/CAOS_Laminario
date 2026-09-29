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
#: Whole-slide sources downloaded at the same time. Zenodo serves about 0.9 MB/s per connection, so the ten NMNH
#: scans (25 GB) take hours one after another; each file still comes over one connection.
WSI_PARALLEL = 8


def _partial(folder: Path, url: str) -> Path:
    """The file a download grows into: one per URL, so parallel downloads never share it and a stopped one resumes."""
    return folder / f".partial-{hashlib.sha1(url.encode('utf-8'), usedforsecurity=False).hexdigest()[:16]}"


def _hash_existing(path: Path) -> tuple[hashlib._Hash, hashlib._Hash, int]:
    sha, md5, size = hashlib.sha256(), hashlib.md5(usedforsecurity=False), 0
    if path.exists():
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(CHUNK), b""):
                sha.update(chunk)
                md5.update(chunk)
                size += len(chunk)
    return sha, md5, size


def download(url: str, folder: Path, attempts: int = 8, pause_s: float = PAUSE_S, max_wait_s: float = 600.0,
             extension: str | None = None) -> dict:
    """Stream a URL into ``folder``, returning its SHA-256, MD5, size and the file's name.

    A download that stops (a network error, a stopped run) resumes where it stopped with an HTTP Range request when
    the server honours it (206); otherwise it starts again from the first byte.
    """
    import time

    import httpx2

    folder.mkdir(parents=True, exist_ok=True)
    partial = _partial(folder, url)
    last_error = None
    wait = BACKOFF_S
    for _ in range(attempts):
        time.sleep(pause_s)
        sha, md5, size = _hash_existing(partial)
        headers = {"User-Agent": USER_AGENT, **({"Range": f"bytes={size}-"} if size else {})}
        try:
            with httpx2.Client(timeout=120.0, follow_redirects=True, headers=headers) as client:
                with client.stream("GET", url) as response:
                    if response.status_code in (429, 503):
                        retry = response.headers.get("retry-after", "")
                        wait = max(wait, float(retry)) if retry.isdigit() else wait
                        raise SourceError(f"{url} answered {response.status_code}")
                    if response.status_code == 416 and size:
                        partial.unlink()
                        raise SourceError(f"{url}: the partial file is longer than the source; starting again")
                    if response.status_code == 200 and size:
                        sha, md5, size = hashlib.sha256(), hashlib.md5(usedforsecurity=False), 0
                        partial.unlink()
                    elif response.status_code not in (200, 206):
                        raise SourceError(f"{url} answered {response.status_code}")
                    content_type = response.headers.get("content-type")
                    with partial.open("ab") as out:
                        for chunk in response.iter_bytes(CHUNK):
                            out.write(chunk)
                            sha.update(chunk)
                            md5.update(chunk)
                            size += len(chunk)
            digest = sha.hexdigest()
            target = folder / f"{digest}.{extension or _extension(url, content_type)}"
            if target.exists():
                partial.unlink()
            else:
                partial.replace(target)
            return {"sha256": digest, "md5": md5.hexdigest(), "bytes": size, "file": target.name,
                    "content_type": content_type}
        except (httpx2.HTTPError, SourceError) as exc:
            last_error = exc
            time.sleep(wait)
            wait = min(wait * 2, max_wait_s)
    raise SourceError(f"{url}: {last_error}")


def extension_of(asset: dict) -> str | None:
    """The file's own extension when the source names the file (a Zenodo download URL ends in ``/content``, and the
    reader tells formats such as NDPI by their extension)."""
    name = str(asset.get("record_id", "")).rsplit("/", 1)[-1]
    suffix = Path(name).suffix.lstrip(".").lower()
    return suffix if asset.get("wsi") and suffix and len(suffix) <= 5 else None


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


def _name_by_extension(lock: dict, acquired: dict[str, dict], folder: Path) -> int:
    """Files acquired before ``extension_of`` existed, renamed to the extension their source names (same bytes)."""
    renamed = 0
    for slide in lock["slides"]:
        for asset in slide["assets"]:
            got, ext = acquired.get(asset["url"]), extension_of(asset)
            if not got or not ext or got["file"].endswith(f".{ext}"):
                continue
            old = folder / got["file"]
            new = folder / f"{got['sha256']}.{ext}"
            if old.exists() and not new.exists():
                old.replace(new)
            got["file"] = new.name
            renamed += 1
    return renamed


def acquire(vault: Path, only: set[str] | None = None, wsi_parallel: int = WSI_PARALLEL) -> dict[str, dict]:
    """Every asset of the lock not yet in the vault: images one by one (paced), whole-slide sources in parallel."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock

    lock = yaml.safe_load(LOCK.read_text(encoding="utf-8"))
    acquired = load()
    folder = vault / "sources"
    guard = Lock()
    wanted: list[tuple[dict, dict]] = []
    renamed = _name_by_extension(lock, acquired, folder)
    if renamed:
        save(acquired)
        print(f"{renamed} acquired files renamed to their own extension", flush=True)
    for slide in lock["slides"]:
        if only and slide["id"] not in only and slide["collection"] not in only:
            continue
        for asset in slide["assets"]:
            known = acquired.get(asset["url"])
            if not (known and (folder / known["file"]).exists()):
                wanted.append((slide, asset))

    def one(slide: dict, asset: dict, pause_s: float) -> None:
        url = asset["url"]
        # An image is retried briefly (the NHM image server answers 500 to a first request it has not rendered yet,
        # then 200); a whole-slide file is worth the long back-off.
        got = download(url, folder, pause_s=pause_s, attempts=8 if asset.get("wsi") else 5,
                       max_wait_s=600.0 if asset.get("wsi") else 60.0, extension=extension_of(asset))
        if asset.get("md5") and got["md5"] != asset["md5"]:
            raise SourceError(f"{url}: MD5 {got['md5']} differs from the record's {asset['md5']}")
        if asset.get("sha256") and got["sha256"] != asset["sha256"]:
            raise SourceError(f"{url}: SHA-256 differs from the index's")
        entry = {"sha256": got["sha256"], "bytes": got["bytes"], "file": got["file"],
                 "retrieved_on": date.today().isoformat()}
        if url.endswith(".zip"):
            entry["open"] = unpack_dicom(folder / got["file"])
        with guard:
            acquired[url] = entry
            save(acquired)
            print(f"{slide['id']}: {got['bytes']:,} bytes {got['sha256'][:12]}", flush=True)

    whole = [(s, a) for s, a in wanted if a.get("wsi")]
    images = [(s, a) for s, a in wanted if not a.get("wsi")]
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, wsi_parallel)) as pool:
        futures = [pool.submit(one, s, a, 0.0) for s, a in whole]
        for s, a in images:
            try:
                one(s, a, PAUSE_S)
            except SourceError as exc:
                errors.append(str(exc))
        for f in futures:
            try:
                f.result()
            except SourceError as exc:
                errors.append(str(exc))
    if errors:
        raise SourceError(f"{len(errors)} downloads failed:\n" + "\n".join(errors))
    return acquired
