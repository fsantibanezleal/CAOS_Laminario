"""The IIIF Image API 3 in front of iipsrv.

iipsrv (IIPImage 1.3, pinned container) reads the pyramid files of the slide store and answers IIIF Image
API 3 requests at level 2. It does not know where the public reaches it, nor any asset's licence, so the
API serves each ``info.json`` itself:

- the identifier is resolved to an asset (a ready pyramid of a published slide; anything else is 404);
- iipsrv's ``info.json`` for that file is fetched on loopback and cached;
- ``id`` becomes the public address of the service and ``rights`` the asset's licence, in the http form the
  IIIF specifications require.

Tiles are the tile server's own bytes. In production nginx sends tile requests straight to iipsrv and caches
them; the API passes them through as well, so the same URLs work in local development and behind nginx.

An identifier is one path segment: the storage key with its slashes percent-encoded.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from urllib.parse import quote, unquote

IMAGE_CONTEXT = "http://iiif.io/api/image/3/context.json"
IMAGE_PROTOCOL = "http://iiif.io/api/image"
INFO_MEDIA_TYPE = f'application/ld+json;profile="{IMAGE_CONTEXT}"'
INFO_CACHE_ENTRIES = 2048


def identifier(storage_key: str) -> str:
    """The IIIF identifier of a stored file: its storage key as one percent-encoded path segment."""
    return quote(storage_key, safe="")


KEY_PATTERN = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")


def storage_key(identifier_text: str) -> str | None:
    """The storage key an identifier names, or None when it is not one the store could hold.

    Storage keys are written by the worker from letters, digits, dots, dashes, underscores and slashes; no
    segment may be ``.`` or ``..``, so a key never leaves the store.
    """
    key = unquote(identifier_text)
    if not KEY_PATTERN.match(key) or any(part in (".", "..") for part in key.split("/")):
        return None
    return key


def upstream_path(key: str) -> str:
    """Path of a file's service on iipsrv (its ``URI_MAP`` takes ``/iiif/`` and the path under its root)."""
    return "/iiif/" + quote(key, safe="/")


def public_service_id(public_base_url: str, key: str) -> str:
    return f"{public_base_url.rstrip('/')}/iiif/{identifier(key)}"


def rewrite_info(upstream: dict, service_id: str, rights: str | None) -> dict:
    """iipsrv's ``info.json`` with the public ``id`` and the asset's ``rights``; nothing else changes."""
    info = {k: v for k, v in upstream.items() if k not in ("@id", "id", "rights")}
    info["@context"] = IMAGE_CONTEXT
    info["id"] = service_id
    info["type"] = "ImageService3"
    info["protocol"] = IMAGE_PROTOCOL
    if rights:
        info["rights"] = rights
    return info


class InfoCache:
    """A small least-recently-used cache of upstream ``info.json`` documents, keyed by storage key."""

    def __init__(self, size: int = INFO_CACHE_ENTRIES):
        self._size = size
        self._items: OrderedDict[str, dict] = OrderedDict()

    def get(self, key: str) -> dict | None:
        value = self._items.get(key)
        if value is not None:
            self._items.move_to_end(key)
        return value

    def put(self, key: str, value: dict) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self._size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()
