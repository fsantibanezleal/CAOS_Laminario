"""What a file is, from its bytes, never from its name.

The ingestion contract accepts JPEG, PNG, WebP, TIFF and BigTIFF (which covers Aperio SVS, Hamamatsu NDPI, Leica SCN
and Philips TIFF), and three multi-file scanner formats that arrive as ZIP archives: 3DHISTECH MRXS, Olympus VSI and
DICOM whole-slide sets. Sniffing recognises the family from magic numbers and, for archives, from the names inside;
whether the file is really readable is the reader's decision afterwards.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

HEADER_BYTES = 4096


@dataclass(frozen=True)
class Sniffed:
    kind: str  # jpeg, png, webp, tiff, bigtiff, dicom, zip-mrxs, zip-vsi, zip-dicom, or what was found instead
    accepted: bool
    detail: str


ACCEPTED = {"jpeg", "png", "webp", "tiff", "bigtiff", "dicom", "zip-mrxs", "zip-vsi", "zip-dicom"}
KNOWN_REFUSED = [
    (b"MZ", "a Windows executable"),
    (b"\x7fELF", "a Linux executable"),
    (b"%PDF", "a PDF document"),
    (b"GIF8", "a GIF image"),
    (b"\x1f\x8b", "a gzip archive"),
    (b"Rar!", "a RAR archive"),
    (b"7z\xbc\xaf\x27\x1c", "a 7-Zip archive"),
    (b"\x00\x00\x00\x18ftyp", "an ISO media file (video or HEIF)"),
    (b"\x00\x00\x00\x1cftyp", "an ISO media file (video or HEIF)"),
    (b"\x00\x00\x00\x20ftyp", "an ISO media file (video or HEIF)"),
]
WSI_KINDS = {"bigtiff", "dicom", "zip-mrxs", "zip-vsi", "zip-dicom"}


def _zip_kind(path: Path) -> Sniffed:
    try:
        with zipfile.ZipFile(path) as archive:
            names = [n.lower() for n in archive.namelist()]
    except zipfile.BadZipFile:
        return Sniffed("zip-damaged", False, "a damaged ZIP archive")
    if any(n.endswith(".mrxs") for n in names):
        return Sniffed("zip-mrxs", True, "a 3DHISTECH MRXS slide in a ZIP archive")
    if any(n.endswith(".vsi") for n in names):
        return Sniffed("zip-vsi", True, "an Olympus VSI slide in a ZIP archive")
    if any(n.endswith(".dcm") or n.split("/")[-1] == "dicomdir" for n in names):
        return Sniffed("zip-dicom", True, "a DICOM whole-slide set in a ZIP archive")
    return Sniffed("zip-other", False, "a ZIP archive without an MRXS, VSI or DICOM slide")


def sniff(path: str | Path) -> Sniffed:
    path = Path(path)
    with open(path, "rb") as handle:
        head = handle.read(HEADER_BYTES)
    if head[:3] == b"\xff\xd8\xff":
        return Sniffed("jpeg", True, "a JPEG image")
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return Sniffed("png", True, "a PNG image")
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return Sniffed("webp", True, "a WebP image")
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return Sniffed("tiff", True, "a TIFF file (plain TIFF, SVS, NDPI, SCN or Philips TIFF)")
    if head[:4] in (b"II+\x00", b"MM\x00+"):
        return Sniffed("bigtiff", True, "a BigTIFF file")
    if len(head) >= 132 and head[128:132] == b"DICM":
        return Sniffed("dicom", True, "a DICOM file")
    if head[:4] == b"PK\x03\x04":
        return _zip_kind(path)
    for magic, label in KNOWN_REFUSED:
        if head.startswith(magic):
            return Sniffed("refused", False, label)
    if not head:
        return Sniffed("empty", False, "an empty file")
    return Sniffed("unknown", False, "a file of an unrecognised type")
