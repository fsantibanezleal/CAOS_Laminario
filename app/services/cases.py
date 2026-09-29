"""A contribution's lifecycle (R-1205, R-1206).

    draft ----submit (every image has its file)----> processing ----every image ready, no job left----> published
      ^                                                   |
      +---------------- an image failed (the reason) -----+

A draft is its contributor's alone: listed, reopened, changed and deleted by them. A change replaces the case's
record and keeps each image whose token (the ``upload_id`` the form chose) it still names, with its file; an image
the case no longer names leaves with its uploads and files. Submitting needs every image to have its file (an
accepted upload, or a remote IIIF service). Publication is automatic, since accounts are invitation-only (U13 adds
hiding and restoring): the worker checks a case after each of its jobs.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.contracts import catalog as c
from app.contracts.ingest import SlideCaseSubmission
from app.db.base import utcnow
from app.db.models import Asset, Slide, Upload, User
from app.services import slides

#: Slide columns a change of the case rewrites; the rest (identity, status, owner, dates) stay.
KEPT = {"id", "short_id", "status", "status_reason", "contributor_id", "created_at", "published_at", "origin"}
#: Asset columns a change rewrites on an image it keeps; its file, processing and status stay.
ASSET_RECORD = ("family", "role", "sort_order", "pixel_size_um", "modality", "stack", "plane_index", "plane_depth_um",
                "polarisation_state", "polarisation_angle_deg", "caption", "licence_uri", "rights_holder", "creator")


class CaseRefused(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class Owned:
    slide: Slide
    uploads: list[Upload]


def _cases():
    return select(Slide).options(selectinload(Slide.assets))


async def owned(db: AsyncSession, user: User, raw_id: str) -> Owned:
    """A case of the signed-in contributor, with its uploads; anyone else's is not found (it is not theirs to know)."""
    from app.db.short_id import normalise

    sid = normalise(raw_id)
    slide = (await db.execute(_cases().where(Slide.short_id == sid))).scalar_one_or_none() if sid else None
    if slide is None or slide.origin != "contribution" or slide.contributor_id != str(user.id):
        raise CaseRefused(404, "no such slide case of yours")
    uploads = (await db.execute(select(Upload).where(Upload.slide_id == slide.id).order_by(Upload.id))).scalars().all()
    return Owned(slide, list(uploads))


def _image(asset: Asset, uploads: list[Upload]) -> c.CaseImageRecord:
    mine = [u for u in uploads if u.asset_id == asset.id]
    last = mine[-1] if mine else None
    has_file = asset.remote_info_url is not None or any(u.status == "accepted" for u in mine)
    return c.CaseImageRecord(
        asset_id=asset.id, token=asset.client_token, family=asset.family, role=asset.role, status=asset.status,
        failure=asset.failure, has_file=has_file, upload_status=last.status if last else None,
        upload_reason=last.reason if last else None, upload_job=last.job_id if last else None)


def summary(case: Owned) -> c.CaseSummary:
    s = case.slide
    return c.CaseSummary(id=s.short_id, status=s.status, status_reason=s.status_reason, name=s.anchor_name,
                         placement=s.placement_node, updated_at=s.updated_at,
                         images=[_image(a, case.uploads) for a in sorted(s.assets, key=lambda a: a.sort_order)])


def record(case: Owned) -> c.CaseRecord:
    s = case.slide
    return c.CaseRecord(**summary(case).model_dump(), submission=json.loads(s.submission_json or "{}"))


async def listing(db: AsyncSession, user: User) -> list[c.CaseSummary]:
    rows = (await db.execute(_cases().where(Slide.origin == "contribution", Slide.contributor_id == str(user.id))
                             .order_by(Slide.updated_at.desc(), Slide.id.desc()))).scalars().all()
    ids = [s.id for s in rows]
    uploads = (await db.execute(select(Upload).where(Upload.slide_id.in_(ids)).order_by(Upload.id))).scalars().all() \
        if ids else []
    return [summary(Owned(s, [u for u in uploads if u.slide_id == s.id])) for s in rows]


def _remove_files(settings: Settings, assets: list[Asset], uploads: list[Upload]) -> None:
    """The files of images that leave a case: their sources, stored derivatives and anything still in quarantine."""
    for upload in uploads:
        if upload.source_path:
            path = Path(upload.source_path)
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
        (settings.quarantine_root / upload.tus_id).unlink(missing_ok=True)
        (settings.quarantine_root / f"{upload.tus_id}.info").unlink(missing_ok=True)
    for asset in assets:
        if asset.storage_key:
            (settings.store_root / asset.storage_key).unlink(missing_ok=True)


async def replace(db: AsyncSession, user: User, raw_id: str, sub: SlideCaseSubmission, resolved,
                  settings: Settings) -> Owned:
    """A draft's new record: every slide column from the case, the images it still names kept with their files."""
    case = await owned(db, user, raw_id)
    slide = case.slide
    if slide.status != "draft":
        raise CaseRefused(409, "only a draft can be changed")
    fresh = slides.slide_from_submission(sub, new_id=slide.short_id, contributor_id=slide.contributor_id,
                                         resolved=resolved)
    for column in Slide.__table__.columns:
        if column.name not in KEPT:
            setattr(slide, column.name, getattr(fresh, column.name))
    slide.updated_at = utcnow()
    kept_by_token = {a.client_token: a for a in slide.assets if a.client_token}
    wanted_tokens = {a.client_token for a in fresh.assets}
    leaving = [a for a in slide.assets if a.client_token not in wanted_tokens]
    _remove_files(settings, leaving, [u for u in case.uploads if u.asset_id in {a.id for a in leaving}])
    for asset in leaving:
        await db.execute(delete(Upload).where(Upload.asset_id == asset.id))
        slide.assets.remove(asset)
        await db.delete(asset)
    columns = [col.name for col in Asset.__table__.columns if col.name not in ("id", "slide_id")]
    for order, new in enumerate(list(fresh.assets)):
        old = kept_by_token.get(new.client_token)
        if old is not None:
            for name in ASSET_RECORD:
                setattr(old, name, getattr(new, name))
            old.sort_order = order
        else:
            # A copy: the freshly built image belongs to a transient slide that must not reach the session.
            added = Asset(**{name: getattr(new, name) for name in columns})
            added.sort_order = order
            slide.assets.append(added)
    await db.commit()
    return await owned(db, user, slide.short_id)


async def remove(db: AsyncSession, user: User, raw_id: str, settings: Settings) -> None:
    case = await owned(db, user, raw_id)
    if case.slide.status != "draft":
        raise CaseRefused(409, "only a draft can be deleted")
    _remove_files(settings, list(case.slide.assets), case.uploads)
    await db.execute(delete(Upload).where(Upload.slide_id == case.slide.id))
    await db.delete(case.slide)
    await db.commit()


async def submit(db: AsyncSession, user: User, raw_id: str) -> Owned:
    case = await owned(db, user, raw_id)
    slide = case.slide
    if slide.status != "draft":
        raise CaseRefused(409, "only a draft can be submitted")
    missing = [i for i in summary(case).images if not i.has_file]
    if missing:
        raise CaseRefused(409, f"{len(missing)} image(s) still need their file")
    slide.status = "processing"
    slide.status_reason = None
    slide.updated_at = utcnow()
    await db.commit()
    await db.run_sync(lambda session: check_publication(session.connection(), slide.id))
    await db.commit()
    return await owned(db, user, slide.short_id)


# --- called by the worker after a job of a case (sync connections) ----------------------------------------------


def check_publication(conn, slide_id: int) -> str | None:
    """Publish a processing contribution whose images are all ready and whose jobs are all done; send it back to
    draft, with the reason, when an image failed. Returns the new status, or None when nothing changed."""
    row = conn.execute(text("SELECT status, origin FROM slide WHERE id = :s"), {"s": slide_id}).one_or_none()
    if row is None or row.origin != "contribution" or row.status != "processing":
        return None
    failed = conn.execute(text("SELECT id, failure FROM asset WHERE slide_id = :s AND status = 'failed'"),
                          {"s": slide_id}).first()
    if failed is not None:
        conn.execute(text("UPDATE slide SET status = 'draft', status_reason = :r, updated_at = :t WHERE id = :s"),
                     {"r": f"an image could not be processed: {failed.failure or 'unknown'}"[:300], "t": utcnow(),
                      "s": slide_id})
        return "draft"
    waiting = conn.execute(text("SELECT COUNT(*) FROM asset WHERE slide_id = :s AND status != 'ready'"),
                           {"s": slide_id}).scalar_one()
    busy = conn.execute(text("SELECT COUNT(*) FROM job WHERE slide_id = :s AND status IN ('queued', 'running')"),
                        {"s": slide_id}).scalar_one()
    if waiting or busy:
        return None
    now = utcnow()
    conn.execute(text("UPDATE slide SET status = 'published', published_at = :t, updated_at = :t WHERE id = :s"),
                 {"t": now, "s": slide_id})
    return "published"


def _slide_of(conn, payload: dict) -> int | None:
    if payload.get("slide_id") is not None:
        return int(payload["slide_id"])
    if payload.get("asset_id") is not None:
        return conn.execute(text("SELECT slide_id FROM asset WHERE id = :a"), {"a": int(payload["asset_id"])}).scalar()
    if payload.get("upload_id") is not None:
        return conn.execute(text("SELECT slide_id FROM upload WHERE id = :u"),
                            {"u": int(payload["upload_id"])}).scalar()
    return None


def after_job(engine: Engine, kind: str, payload: dict, failed: bool, error: str | None) -> str | None:
    """The worker's hook after any job: an image whose processing failed is marked and its case sent back to draft;
    any job of a case may be the last one it waited for. Returns the case's new status, if it changed."""
    with engine.begin() as conn:
        if failed and kind == "process_asset" and payload.get("asset_id") is not None:
            conn.execute(text("UPDATE asset SET status = 'failed', failure = :f WHERE id = :a"),
                         {"f": (error or "failed").splitlines()[0][:300], "a": int(payload["asset_id"])})
        slide_id = _slide_of(conn, payload)
        return check_publication(conn, slide_id) if slide_id is not None else None
