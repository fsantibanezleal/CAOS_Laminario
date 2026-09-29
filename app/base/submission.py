"""A lock entry as a slide-case submission of the ingestion contract (origin ``base``).

Every asset carries its source block (URL, record id, retrieval date, SHA-256 of the retrieved bytes) from
``acquired.json``. A focal stack (``stack: policy``) is expanded here, from the acquired file itself: its planes are
read and the z-plane policy (U2) chooses the ones kept, each becoming a ``z_plane`` asset with its original index
and depth.
"""

from __future__ import annotations

from pathlib import Path

from app.imaging import reader, zstack

#: Measured bytes of pyramid per source pixel at JPEG Q85 (dossier 04: 97 KB per megapixel).
BYTES_PER_PIXEL = 0.097


def source_block(asset: dict, acquired: dict[str, dict]) -> dict:
    got = acquired[asset["url"]]
    return {"url": asset["url"], "record_id": asset["record_id"], "retrieved_on": got["retrieved_on"],
            "sha256": got["sha256"]}


def source_path(asset: dict, acquired: dict[str, dict], vault: Path) -> Path:
    got = acquired[asset["url"]]
    return vault / "sources" / got.get("open", got["file"])


def _plain(asset: dict, acquired: dict[str, dict]) -> dict:
    out = {"family": asset["family"], "role": asset["role"], "licence": asset["licence"],
           "source": source_block(asset, acquired)}
    for field in ("rights_holder", "creator", "modality", "pixel_size_um", "caption", "polarisation"):
        if asset.get(field) not in (None, ""):
            out[field] = asset[field]
    return out


def stack_assets(slide_id: str, asset: dict, acquired: dict[str, dict], vault: Path) -> list[dict]:
    info = reader.read_info(source_path(asset, acquired, vault))
    planes = [zstack.Plane(p.index, p.depth_um or 0.0) for p in info.planes]
    chosen = zstack.select_planes(planes, int(info.width * info.height * BYTES_PER_PIXEL))
    out = []
    for plane in chosen.kept:
        entry = _plain(asset, acquired)
        entry["role"] = "z_plane"
        entry["plane"] = {"index": plane.index, "depth_um": plane.depth_um, "stack": "focus"}
        entry["caption"] = f"focal plane {plane.index + 1} of {chosen.total}"
        out.append(entry)
    return out


def submission(slide: dict, acquired: dict[str, dict], vault: Path | None = None,
               origins: list[dict] | None = None) -> dict:
    """The submission for a lock slide; ``origins``, when given, receives the lock asset behind each asset."""
    assets: list[dict] = []
    for asset in slide["assets"]:
        if asset.get("stack") == "policy":
            if vault is None:
                raise ValueError("a focal stack is expanded from its acquired file: the vault is needed")
            planes = stack_assets(slide["id"], asset, acquired, vault)
        else:
            planes = [_plain(asset, acquired)]
        assets += planes
        if origins is not None:
            origins += [asset] * len(planes)
    return {"origin": "base", "slide": slide["slide"], "specimen": slide["specimen"],
            "placement": slide["placement"], "assets": assets}
