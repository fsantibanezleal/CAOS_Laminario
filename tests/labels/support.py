"""Slide records built in memory from the standard contribution, changed as a test needs."""

from __future__ import annotations

from app.config import Settings
from app.contracts import catalog as c
from app.contracts.ingest import SlideCaseSubmission
from app.db.base import utcnow
from app.services import catalog, slides
from tests import payloads

HOST = "https://laminario.ml.fasl-work.com"


def record(short_id: str = "9422P6AW", *, slide: dict | None = None, specimen: dict | None = None,
           drop: tuple[str, ...] = ()) -> c.SlideRecord:
    payload = payloads.contribution()
    payload["slide"].update(slide or {})
    payload["specimen"].update(specimen or {})
    for key in drop:
        payload["slide"].pop(key, None)
        payload["specimen"].pop(key, None)
    row = slides.slide_from_submission(SlideCaseSubmission.model_validate(payload), new_id=short_id)
    row.created_at = row.updated_at = row.published_at = utcnow()
    row.status = "published"
    for i, asset in enumerate(row.assets):
        asset.id, asset.status = i + 1, "ready"
    return catalog.slide_record(row, Settings(_env_file=None, public_base_url=HOST))
