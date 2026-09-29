"""Annotations on a slide's assets, stored and read as W3C Web Annotations (R-1108).

An annotation's target is always the asset's own image: its IIIF image id (the ``info.json`` address without the
file name) for a pyramid or a remote IIIF image, or the image's address for a plain image. The selector locates the
region on it; the bodies say what the author wrote. Anyone reads the annotations of a published slide; a signed-in
account adds them; the author or a curator removes one.
"""

from __future__ import annotations

import json
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import roles
from app.config import Settings
from app.contracts import catalog as c
from app.contracts.annotations import AnnotationIn
from app.db.base import utcnow
from app.db.models import Annotation, Asset, Slide, User
from app.services.catalog import media_record

CONTEXT = "http://www.w3.org/ns/anno.jsonld"
MAX_PER_ASSET = 1000


def target_source(asset: Asset, settings: Settings) -> str | None:
    media = media_record(asset, settings)
    if media.iiif_info_url:
        return media.iiif_info_url.removesuffix("/info.json")
    return media.image_url


def w3c(row: Annotation, author: User, source: str, settings: Settings) -> dict:
    return {
        "@context": CONTEXT,
        "id": f"{settings.public_base_url}/api/annotations/{row.public_id}",
        "type": "Annotation",
        "motivation": "commenting",
        "creator": {"type": "Person", "name": author.display_name},
        "created": row.created_at.isoformat(timespec="seconds") + "Z",
        "modified": row.updated_at.isoformat(timespec="seconds") + "Z",
        "body": json.loads(row.body_json),
        "target": {"source": source, "selector": json.loads(row.selector_json)},
    }


def record(row: Annotation, author: User, source: str, settings: Settings, reader: User | None) -> c.AnnotationRecord:
    removable = reader is not None and (reader.id == row.author_id or roles.allowed(reader.role, "moderate"))
    return c.AnnotationRecord(id=row.public_id, asset_id=row.asset_id, author=author.display_name,
                              removable=removable, annotation=w3c(row, author, source, settings))


async def published_asset(db: AsyncSession, slide: Slide, asset_id: int) -> Asset | None:
    return next((a for a in slide.assets if a.id == asset_id and a.status == "ready"), None)


async def listing(db: AsyncSession, slide: Slide, asset: Asset, settings: Settings,
                  reader: User | None) -> list[c.AnnotationRecord]:
    rows = (await db.execute(select(Annotation, User).join(User, User.id == Annotation.author_id)
                             .where(Annotation.asset_id == asset.id).order_by(Annotation.id))).all()
    source = target_source(asset, settings) or ""
    return [record(row, author, source, settings, reader) for row, author in rows]


async def create(db: AsyncSession, slide: Slide, asset: Asset, payload: AnnotationIn, author: User,
                 settings: Settings) -> c.AnnotationRecord:
    count = len((await db.execute(select(Annotation.id).where(Annotation.asset_id == asset.id))).all())
    if count >= MAX_PER_ASSET:
        raise ValueError(f"this image already holds {MAX_PER_ASSET} annotations")
    now = utcnow()
    row = Annotation(public_id=secrets.token_hex(12), slide_id=slide.id, asset_id=asset.id, author_id=author.id,
                     body_json=json.dumps([b.model_dump(exclude_none=True) for b in payload.body], ensure_ascii=False),
                     selector_json=json.dumps(payload.target.selector.model_dump(exclude_none=True)),
                     created_at=now, updated_at=now)
    db.add(row)
    await db.commit()
    return record(row, author, target_source(asset, settings) or "", settings, author)


async def by_public_id(db: AsyncSession, public_id: str) -> Annotation | None:
    return (await db.execute(select(Annotation).where(Annotation.public_id == public_id))).scalar_one_or_none()


def may_remove(row: Annotation, user: User) -> bool:
    return user.id == row.author_id or roles.allowed(user.role, "moderate")
