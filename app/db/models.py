"""Tables for the slide case (``slide``, ``asset``), processing (``job``, ``job_event``) and accounts (``user``,
``accesstoken``, ``invitation``), uploads (``upload``) and the GBIF taxon cache (``taxon``).

Other tables arrive with the units that need them (users and invitations, jobs, uploads, identifications),
each with its own migration. Columns mirror the ingestion contract; the catalog record is assembled from them.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID
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
    #: The source did not record the physical slide (most open photomicrographs); the format is assumed.
    format_assumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
    #: The Nickel-Strunz code of a mineral (from the vocabulary or declared) or the Kikuchi category of an ice crystal.
    anchor_classification: Mapped[str | None] = mapped_column(String(16))
    #: The part of the organism the slide shows (parts vocabulary), and whether it is recent, fossil or in amber.
    part: Mapped[str | None] = mapped_column(String(40))
    preservation: Mapped[str] = mapped_column(String(10), nullable=False, default="recent")
    host_ref: Mapped[str | None] = mapped_column(String(200))
    host_name: Mapped[str | None] = mapped_column(String(200))
    host_rank: Mapped[str | None] = mapped_column(String(32))
    type_status: Mapped[str | None] = mapped_column(String(16))

    collected_on: Mapped[str | None] = mapped_column(String(10))
    collector: Mapped[str | None] = mapped_column(String(120))
    locality_text: Mapped[str | None] = mapped_column(String(300))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    #: ISO 3166-1 alpha-2: stated by a source, or implied by the coordinates (app/collections/places.py).
    country: Mapped[str | None] = mapped_column(String(2), index=True)
    uncertainty_m: Mapped[float | None] = mapped_column(Float)
    geoprivacy: Mapped[str] = mapped_column(String(10), nullable=False, default="open")

    placement_node: Mapped[str] = mapped_column(String(120), nullable=False)
    #: What search matches (app/services/search.py); the FTS5 table slide_search follows it by triggers.
    search_text: Mapped[str | None] = mapped_column(Text)
    #: Why a contribution is back to draft (an image failed), shown to its contributor.
    status_reason: Mapped[str | None] = mapped_column(String(300))
    #: A contribution's case as its contributor last sent it, to reopen the form (U12).
    submission_json: Mapped[str | None] = mapped_column(Text)
    placement_override_reason: Mapped[str | None] = mapped_column(String(300))
    #: The contributor's user id (a UUID), linked to the user table when accounts arrive.
    contributor_id: Mapped[str | None] = mapped_column(String(36))

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    # The community (U13): the node the identifications agree on, its rank when it is a taxon, and the badge the
    # slide checks and the community give (verified, needs_id, reference); kept so the Identify queue can filter.
    community_node: Mapped[str | None] = mapped_column(String(200))
    community_rank: Mapped[str | None] = mapped_column(String(32))
    badge: Mapped[str | None] = mapped_column(String(12))
    # The status a hidden slide returns to when a curator restores it.
    hidden_from: Mapped[str | None] = mapped_column(String(16))

    assets: Mapped[list[Asset]] = relationship(
        back_populates="slide", cascade="all, delete-orphan", order_by="Asset.sort_order"
    )

    __table_args__ = (
        Index(None, "status"),
        Index(None, "placement_node"),
        Index(None, "anchor_kind", "anchor_ref"),
        Index(None, "badge"),
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
    #: The contributor's token for this image in the case (its upload_id): an edited case keeps the image it names.
    client_token: Mapped[str | None] = mapped_column(String(128))
    #: Why the image's verification or processing failed, shown to its contributor.
    failure: Mapped[str | None] = mapped_column(String(300))

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
    #: IIIF Image API version of a remote service (2 or 3), recorded when the remote-asset contract is checked.
    remote_iiif_version: Mapped[int | None] = mapped_column(Integer)
    #: The file processing reads (the upload quarantine or the base-collection vault); set by U5 and U8.
    source_path: Mapped[str | None] = mapped_column(String(500))
    #: Level-0 fidelity of the written pyramid (U2's measured PSNR) and the tile codec and quality kept.
    psnr_db: Mapped[float | None] = mapped_column(Float)
    codec: Mapped[str | None] = mapped_column(String(12))

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    slide: Mapped[Slide] = relationship(back_populates="assets")

    __table_args__ = (Index(None, "slide_id"),)


class Job(Base):
    """A unit of processing, claimed and run by the worker. Its events are in ``job_event``."""

    __tablename__ = "job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The id the API and the browser use: random, so job numbers cannot be enumerated.
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    #: queued, running, succeeded, failed, cancelled
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="queued")
    #: Heavy jobs (pyramids, fusion) run one at a time.
    heavy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    result_json: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(String(500))
    timeout_s: Mapped[int] = mapped_column(Integer, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    slide_id: Mapped[int | None] = mapped_column(ForeignKey("slide.id", ondelete="SET NULL"))
    worker: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (Index(None, "status", "id"), Index(None, "slide_id"))


class JobEvent(Base):
    """One entry of a job's journal: numbered per job, so a reconnecting client resumes after the last it saw."""

    __tablename__ = "job_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    #: queued, started, progress, log, requeued, succeeded, failed, cancelled
    event: Mapped[str] = mapped_column(String(16), nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (UniqueConstraint("job_id", "seq"),)


class User(SQLAlchemyBaseUserTableUUID, Base):
    """An account. There is no open sign-up: every account comes from an invitation (``invitation``).

    fastapi-users provides id, email, hashed_password, is_active, is_superuser and is_verified; ``role`` is the
    source of authorisation (``is_superuser`` mirrors ``role == "admin"``).
    """

    #: contributor, identifier, curator or admin
    role: Mapped[str] = mapped_column(String(12), nullable=False, default="contributor")
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    #: The public address of the account's profile (U14, ``app/accounts/handles.py``); never the email.
    handle: Mapped[str | None] = mapped_column(String(64), unique=True)


class AccessToken(SQLAlchemyBaseAccessTokenTableUUID, Base):
    """A signed-in session: an opaque token in a cookie, its row here, deleted at sign-out."""


class Invitation(Base):
    """The only way to an account: a single-use link with an expiry, issued by a curator or an admin.

    Only the SHA-256 of the token is stored, so a copy of the database cannot be used to register.
    """

    __tablename__ = "invitation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    #: The address the invitation is for, when it names one; registration must then use it.
    email: Mapped[str | None] = mapped_column(String(320))
    role: Mapped[str] = mapped_column(String(12), nullable=False)
    #: The issuing account; null when issued from the server's command line (the first admin).
    issued_by_id: Mapped[object | None] = mapped_column(GUID, ForeignKey("user.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    used_by_id: Mapped[object | None] = mapped_column(GUID, ForeignKey("user.id", ondelete="SET NULL"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    mailed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Upload(Base):
    """One file sent through tusd for one asset of a contributor's draft.

    uploading (pre-create accepted it) -> received (tusd has every byte) -> accepted (verified, in the source store,
    processing queued) or rejected (with the reason); cancelled when the client terminates it.
    """

    __tablename__ = "upload"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The id tusd stores the upload under, chosen by the pre-create hook.
    tus_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[object] = mapped_column(GUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    slide_id: Mapped[int] = mapped_column(ForeignKey("slide.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("asset.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255))
    declared_type: Mapped[str | None] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    wsi: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="uploading")
    sha256: Mapped[str | None] = mapped_column(String(64))
    sniffed: Mapped[str | None] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(String(300))
    source_path: Mapped[str | None] = mapped_column(String(500))
    job_id: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (Index(None, "user_id", "status"), Index(None, "asset_id"))


class Taxon(Base):
    """A GBIF backbone taxon a slide or a host refers to, with its lineage, so placement never waits on the network.

    Filled on first use from the GBIF API (``app.collections.taxa``); ``accepted_key`` is set when the key a slide
    gives is a synonym, and placement then uses the accepted taxon.
    """

    __tablename__ = "taxon"

    key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rank: Mapped[str] = mapped_column(String(32), nullable=False)
    #: accepted, doubtful or synonym
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    accepted_key: Mapped[int | None] = mapped_column(Integer)
    #: The keys of the accepted taxon's ancestors, kingdom first, as a JSON list.
    lineage_json: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Annotation(Base):
    """A W3C Web Annotation on one asset of a slide (U11): a region of the image and what a person wrote about it.

    ``body_json`` and ``selector_json`` hold the parts the author gave, validated (``app/contracts/annotations.py``);
    the annotation's id, target source, creator and dates are the server's, set when it is read.
    """

    __tablename__ = "annotation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    slide_id: Mapped[int] = mapped_column(ForeignKey("slide.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("asset.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[object] = mapped_column(GUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    body_json: Mapped[str] = mapped_column(Text, nullable=False)
    selector_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    #: Hidden by a curator (U13): not served, kept with the moderation action that says why.
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (Index(None, "asset_id"),)


class Identification(Base):
    """What an account (or, for a base slide, the source) says a slide shows (U13, dossier 15).

    The anchor is stored as given and resolved, with its lineage as it was when the identification was made, so the
    agreement rule never needs the network. An account has one current identification per slide.
    """

    __tablename__ = "identification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    slide_id: Mapped[int] = mapped_column(ForeignKey("slide.id", ondelete="CASCADE"), nullable=False)
    #: The account, or None for the source's determination of a base slide.
    user_id: Mapped[object | None] = mapped_column(GUID, ForeignKey("user.id", ondelete="CASCADE"))
    anchor_kind: Mapped[str] = mapped_column(String(12), nullable=False)
    anchor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    anchor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    anchor_rank: Mapped[str | None] = mapped_column(String(32))
    anchor_classification: Mapped[str | None] = mapped_column(String(16))
    lineage_json: Mapped[str] = mapped_column(Text, nullable=False)
    #: The slide's anchor, as a lineage, when the identification was made (what an explicit disagreement is with).
    previous_lineage_json: Mapped[str | None] = mapped_column(Text)
    #: For an identification of an ancestor of the slide's anchor: whether it disagrees with the finer anchor.
    disagreement: Mapped[bool | None] = mapped_column(Boolean)
    body: Mapped[str | None] = mapped_column(String(1000))
    current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (Index(None, "slide_id"), Index(None, "user_id"))


class SlideVote(Base):
    """An identifier's answer to "can the community anchor still be improved?" (U13): one per account and slide,
    cleared when the community anchor changes."""

    __tablename__ = "slide_vote"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slide_id: Mapped[int] = mapped_column(ForeignKey("slide.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[object] = mapped_column(GUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    #: True: as good as it can be; False: it still needs identification.
    as_good_as_it_can_be: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (UniqueConstraint("slide_id", "user_id"),)


class Flag(Base):
    """A signed-in account's report of a slide, an identification or an annotation for the curators (U13)."""

    __tablename__ = "flag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    target_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[str] = mapped_column(String(32), nullable=False)
    slide_id: Mapped[int] = mapped_column(ForeignKey("slide.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[object] = mapped_column(GUID, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    resolved_by_id: Mapped[object | None] = mapped_column(GUID, ForeignKey("user.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolution: Mapped[str | None] = mapped_column(String(1000))

    __table_args__ = (Index(None, "slide_id"), Index(None, "resolved_at"))


class ModerationAction(Base):
    """A curator's hiding or restoring of a slide, an identification or an annotation, with the reason (U13)."""

    __tablename__ = "moderation_action"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[object | None] = mapped_column(GUID, ForeignKey("user.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    target_id: Mapped[str] = mapped_column(String(32), nullable=False)
    slide_id: Mapped[int] = mapped_column(ForeignKey("slide.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (Index(None, "target_kind", "target_id"),)
