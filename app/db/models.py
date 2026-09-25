"""Tables for the slide case: ``slide`` and ``asset``.

Other tables arrive with the units that need them (users and invitations, jobs, uploads, identifications),
each with its own migration. Columns mirror the ingestion contract; the catalog record is assembled from them.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow


class Slide(Base):
    __tablename__ = "slide"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    short_id: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    #: draft, processing, published, hidden
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    #: base (the curated collection) or contribution
    origin: Mapped[str] = mapped_column(String(16), nullable=False)

    format_code: Mapped[str] = mapped_column(String(16), nullable=False)
    width_mm: Mapped[float] = mapped_column(Float, nullable=False)
    height_mm: Mapped[float] = mapped_column(Float, nullable=False)
    coverslip_code: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    coverslip_long_mm: Mapped[float | None] = mapped_column(Float)
    coverslip_short_mm: Mapped[float | None] = mapped_column(Float)

    preparation: Mapped[str] = mapped_column(String(24), nullable=False)
    stain: Mapped[str | None] = mapped_column(String(80))
    mountant: Mapped[str | None] = mapped_column(String(80))
    catalogue_number: Mapped[str | None] = mapped_column(String(64))
    label_note: Mapped[str | None] = mapped_column(String(160))
    prepared_on: Mapped[str | None] = mapped_column(String(10))
    preparer: Mapped[str | None] = mapped_column(String(120))

    anchor_kind: Mapped[str] = mapped_column(String(12), nullable=False)
    anchor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    anchor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    anchor_rank: Mapped[str | None] = mapped_column(String(32))
    host_ref: Mapped[str | None] = mapped_column(String(200))
    host_name: Mapped[str | None] = mapped_column(String(200))
    host_rank: Mapped[str | None] = mapped_column(String(32))
    type_status: Mapped[str | None] = mapped_column(String(16))

    collected_on: Mapped[str | None] = mapped_column(String(10))
    collector: Mapped[str | None] = mapped_column(String(120))
    locality_text: Mapped[str | None] = mapped_column(String(300))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    uncertainty_m: Mapped[float | None] = mapped_column(Float)
    geoprivacy: Mapped[str] = mapped_column(String(10), nullable=False, default="open")

    placement_node: Mapped[str] = mapped_column(String(120), nullable=False)
    placement_override_reason: Mapped[str | None] = mapped_column(String(300))
    #: The contributor's user id (a UUID), linked to the user table when accounts arrive.
    contributor_id: Mapped[str | None] = mapped_column(String(36))

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    assets: Mapped[list[Asset]] = relationship(
        back_populates="slide", cascade="all, delete-orphan", order_by="Asset.sort_order"
    )

    __table_args__ = (
        Index(None, "status"),
        Index(None, "placement_node"),
        Index(None, "anchor_kind", "anchor_ref"),
    )


class Asset(Base):
    __tablename__ = "asset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slide_id: Mapped[int] = mapped_column(ForeignKey("slide.id", ondelete="CASCADE"), nullable=False)
    family: Mapped[str] = mapped_column(String(8), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: pyramid (served by the tile server), image (a plain file), remote_iiif (another institution's service)
    media_kind: Mapped[str] = mapped_column(String(12), nullable=False)
    #: pending, ready, failed
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")

    width_px: Mapped[int | None] = mapped_column(Integer)
    height_px: Mapped[int | None] = mapped_column(Integer)
    pixel_size_um: Mapped[float | None] = mapped_column(Float)
    modality: Mapped[str | None] = mapped_column(String(16))
    stack: Mapped[str | None] = mapped_column(String(64))
    plane_index: Mapped[int | None] = mapped_column(Integer)
    plane_depth_um: Mapped[float | None] = mapped_column(Float)
    polarisation_state: Mapped[str | None] = mapped_column(String(4))
    polarisation_angle_deg: Mapped[float | None] = mapped_column(Float)
    caption: Mapped[str | None] = mapped_column(String(300))

    licence_uri: Mapped[str] = mapped_column(String(200), nullable=False)
    rights_holder: Mapped[str | None] = mapped_column(String(200))
    creator: Mapped[str | None] = mapped_column(String(200))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_record_id: Mapped[str | None] = mapped_column(String(200))
    source_retrieved_on: Mapped[date | None] = mapped_column(Date)
    source_sha256: Mapped[str | None] = mapped_column(String(64))

    #: Path of the stored file inside the slide store, relative to the store root.
    storage_key: Mapped[str | None] = mapped_column(String(300))
    bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    remote_info_url: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    slide: Mapped[Slide] = relationship(back_populates="assets")

    __table_args__ = (Index(None, "slide_id"),)
