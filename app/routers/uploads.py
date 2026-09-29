"""Uploads: tusd's hooks, and the contributor's view of its uploads.

tusd (on loopback, exposed by nginx at ``/files/``) calls ``POST /api/_internal/tus-hook`` with each hook event and the
client's ``Cookie`` forwarded, so the uploader is authenticated with its normal session. nginx refuses
``/api/_internal/`` from outside; tusd reaches the API directly.

- ``pre-create`` applies ``app/uploads/policy.py``: a refusal is answered with ``RejectUpload`` and the status and
  reason tusd returns to the client (a non-2xx answer to a hook would reach the client as a bare 500);
  an accepted upload is recorded and given its tus id.
- ``post-finish`` marks the upload received and queues ``verify_upload`` for the worker (checksums of
  multi-gigabyte files do not belong in a hook with a 15-second timeout).
- ``post-terminate`` marks it cancelled.
"""

# No ``from __future__ import annotations``: dependency aliases are defined inside ``routers``.
import json
import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import Integer, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import roles
from app.accounts.users import Accounts
from app.contracts import catalog as c
from app.db import short_id
from app.db.base import utcnow
from app.db.models import Asset, Slide, Upload, User
from app.db.session import session
from app.jobs import queue
from app.uploads import policy

ACTIVE = ("uploading", "received", "accepted")


def refuse(refusal: policy.Refusal) -> dict[str, Any]:
    return {"RejectUpload": True,
            "HTTPResponse": {"StatusCode": refusal.status, "Body": json.dumps({"detail": refusal.reason}),
                             "Header": {"Content-Type": "application/json"}}}


def upload_record(upload: Upload, slide_short_id: str) -> c.UploadRecord:
    return c.UploadRecord(id=upload.id, slide_id=slide_short_id, asset_id=upload.asset_id, filename=upload.filename,
                          size=upload.size, wsi=upload.wsi, status=upload.status, sniffed=upload.sniffed,
                          sha256=upload.sha256, reason=upload.reason, job_id=upload.job_id,
                          created_at=upload.created_at, finished_at=upload.finished_at)


async def pre_create(event: dict, user: User | None, db: AsyncSession, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    if user is None:
        return refuse(policy.Refusal(401, "sign in to upload"))
    if not roles.allowed(user.role, "submit"):
        return refuse(policy.Refusal(403, f"the {user.role} role cannot submit slides"))
    upload = event.get("Upload", {})
    meta = upload.get("MetaData") or {}
    wanted = short_id.normalise(meta.get("slide", ""))
    slide = (await db.execute(select(Slide).where(Slide.short_id == wanted))).scalar_one_or_none() if wanted else None
    if slide is None or slide.contributor_id != str(user.id):
        return refuse(policy.Refusal(403, "the upload must name one of your slide cases (metadata 'slide')"))
    if slide.status != "draft":
        return refuse(policy.Refusal(409, "images can be added only while the slide case is a draft"))
    try:
        asset_id = int(meta.get("asset", ""))
    except ValueError:
        return refuse(policy.Refusal(400, "the upload must name the image it is for (metadata 'asset')"))
    asset = await db.get(Asset, asset_id)
    if asset is None or asset.slide_id != slide.id or asset.media_kind == "remote_iiif":
        return refuse(policy.Refusal(404, "no such image in this slide case"))
    if asset.status != "pending":
        return refuse(policy.Refusal(409, "this image already has its file"))
    busy = (await db.execute(select(func.count()).select_from(Upload)
                             .where(Upload.asset_id == asset.id, Upload.status.in_(("uploading", "received"))))
            ).scalar_one()
    if busy:
        return refuse(policy.Refusal(409, "an upload for this image is already in progress; resume that one"))
    size = None if upload.get("SizeIsDeferred") else upload.get("Size")
    if refusal := policy.check_size(size, settings.max_upload_bytes):
        return refuse(refusal)
    filename = (meta.get("filename") or "")[:255] or None
    wsi = policy.is_wsi(filename, size, settings.wsi_min_bytes)
    used_bytes, used_wsi = (await db.execute(
        select(func.coalesce(func.sum(Upload.size), 0), func.coalesce(func.sum(cast(Upload.wsi, Integer)), 0))
        .where(Upload.user_id == user.id, Upload.status.in_(ACTIVE))
    )).one()
    if refusal := policy.check_quota(int(used_bytes), int(used_wsi), size, wsi, settings.quota_bytes,
                                     settings.quota_wsi):
        return refuse(refusal)
    fraction = policy.volume_fraction_used(settings.data_root)
    if refusal := policy.check_volume(wsi, fraction, settings.wsi_block_fraction):
        return refuse(refusal)
    tus_id = secrets.token_hex(16)
    db.add(Upload(tus_id=tus_id, user_id=user.id, slide_id=slide.id, asset_id=asset.id, filename=filename,
                  declared_type=(meta.get("filetype") or "")[:100] or None, size=size, wsi=wsi, status="uploading"))
    await db.commit()
    return {"ChangeFileInfo": {"ID": tus_id}}


async def post_finish(event: dict, db: AsyncSession, request: Request) -> dict[str, Any]:
    upload_event = event.get("Upload", {})
    upload = (await db.execute(select(Upload).where(Upload.tus_id == upload_event.get("ID")))).scalar_one_or_none()
    if upload is None:
        return {}
    upload.status = "received"
    upload.finished_at = utcnow()
    await db.commit()
    path = (upload_event.get("Storage") or {}).get("Path")
    _, job = await run_in_threadpool(queue.enqueue, request.app.state.sync_engine, "verify_upload",
                                     {"upload_id": upload.id, "path": path}, slide_id=upload.slide_id)
    await db.execute(update(Upload).where(Upload.id == upload.id).values(job_id=job))
    await db.commit()
    return {}


async def post_terminate(event: dict, db: AsyncSession) -> dict[str, Any]:
    tus_id = event.get("Upload", {}).get("ID")
    await db.execute(update(Upload).where(Upload.tus_id == tus_id, Upload.status == "uploading")
                     .values(status="cancelled", finished_at=utcnow()))
    await db.commit()
    return {}


def routers(accounts: Accounts) -> list[APIRouter]:
    api = APIRouter(tags=["uploads"])
    Db = Annotated[AsyncSession, Depends(session)]
    Visitor = Annotated[User | None, Depends(accounts.optional)]
    Signed = Annotated[User, Depends(accounts.current)]

    @api.post("/api/_internal/tus-hook", include_in_schema=False)
    async def tus_hook(request: Request, db: Db, user: Visitor) -> dict[str, Any]:
        body = await request.json()
        kind, event = body.get("Type"), body.get("Event", {})
        if kind == "pre-create":
            return await pre_create(event, user, db, request)
        if kind == "post-finish":
            return await post_finish(event, db, request)
        if kind == "post-terminate":
            return await post_terminate(event, db)
        return {}

    @api.get("/api/uploads", response_model=list[c.UploadRecord])
    async def my_uploads(db: Db, user: Signed) -> list[c.UploadRecord]:
        rows = (await db.execute(select(Upload, Slide.short_id).join(Slide, Slide.id == Upload.slide_id)
                                 .where(Upload.user_id == user.id).order_by(Upload.id.desc()))).all()
        return [upload_record(upload, short) for upload, short in rows]

    @api.get("/api/uploads/{upload_id}", response_model=c.UploadRecord)
    async def one_upload(upload_id: int, db: Db, user: Signed) -> c.UploadRecord:
        row = (await db.execute(select(Upload, Slide.short_id).join(Slide, Slide.id == Upload.slide_id)
                                .where(Upload.id == upload_id))).first()
        if row is None or (row[0].user_id != user.id and not roles.allowed(user.role, "moderate")):
            raise HTTPException(status_code=404, detail="no such upload of yours")
        return upload_record(*row)

    return [api]
