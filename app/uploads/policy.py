"""The rules an upload must pass before it may start (tusd's pre-create hook).

- The uploader is signed in with a role that may submit, owns the slide case (a draft), and the asset is one of its
  pending images that is not a remote IIIF service.
- The size is declared up front (no deferred length), at least one byte, at most ``max_upload_bytes``.
- **Quotas per account**: the bytes of its uploads (in progress and accepted) stay within ``quota_bytes``; whole-slide
  images within ``quota_wsi``. An upload counts as a whole-slide image when its declared name has a scanner extension
  or its size is at least ``wsi_min_bytes``.
- **The disk budget**: while the data volume is fuller than ``wsi_block_fraction`` (90 percent), whole-slide uploads
  are refused and the answer says why (the design document's tier-A rule); ordinary photographs still go.

Every refusal is an ``Refusal(status, reason)`` the hook turns into tusd's ``RejectUpload`` with that status.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

WSI_EXTENSIONS = {".svs", ".ndpi", ".vms", ".vmu", ".scn", ".mrxs", ".vsi", ".bif", ".dcm", ".zip", ".btf", ".isyntax"}


@dataclass(frozen=True)
class Refusal:
    status: int
    reason: str


def is_wsi(filename: str | None, size: int, wsi_min_bytes: int) -> bool:
    suffix = Path(filename or "").suffix.lower()
    return suffix in WSI_EXTENSIONS or size >= wsi_min_bytes


def volume_fraction_used(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return usage.used / usage.total


def check_size(size: int | None, max_bytes: int) -> Refusal | None:
    if size is None:
        return Refusal(400, "the upload must declare its length (Upload-Length)")
    if size < 1:
        return Refusal(400, "an empty file cannot be uploaded")
    if size > max_bytes:
        return Refusal(413, f"the file is {size / 1e9:.2f} GB; the limit is {max_bytes / 1e9:.0f} GB per file")
    return None


def check_quota(used_bytes: int, used_wsi: int, size: int, wsi: bool, quota_bytes: int, quota_wsi: int
                ) -> Refusal | None:
    if used_bytes + size > quota_bytes:
        left = max(quota_bytes - used_bytes, 0)
        return Refusal(413, f"this upload needs {size / 1e6:.1f} MB and your account has {left / 1e6:.1f} MB left "
                            f"of its {quota_bytes / 1e9:.1f} GB")
    if wsi and used_wsi + 1 > quota_wsi:
        return Refusal(413, f"your account has used its {quota_wsi} whole-slide images")
    return None


def check_volume(wsi: bool, fraction_used: float, block_fraction: float) -> Refusal | None:
    if wsi and fraction_used > block_fraction:
        return Refusal(507, f"the collection's disk is {fraction_used * 100:.0f} percent full; whole-slide uploads "
                            f"resume when it is below {block_fraction * 100:.0f} percent")
    return None
