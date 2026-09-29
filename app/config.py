"""Runtime configuration, read from the environment (prefix ``LAMINARIO_``) and the local ``.env``.

Every variable is documented in ``.env.example``. Defaults are for local development; production values
come from the server's environment file, never from the repository.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.version import ROOT


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LAMINARIO_", env_file=ROOT / ".env", extra="ignore", env_ignore_empty=True
    )

    #: ``development`` locally, ``production`` on the server.
    env: Literal["development", "production"] = "development"
    #: The address the public reaches the app at; permalinks and QR codes are built from it.
    public_base_url: str = "http://127.0.0.1:8147"
    #: Root of the slide store, the upload quarantine, the tile cache and the database.
    data_root: Path = ROOT / ".data"
    #: The IIIF tile server (iipsrv), reached on loopback. The API asks it for info.json; in production
    #: nginx sends tile requests to it directly, locally the API passes them through.
    iipsrv_url: str = "http://127.0.0.1:8149"
    #: Signs password-reset links. Required in production (the server's environment file, from the vault);
    #: locally a missing value is replaced by a random one for the life of the process.
    secret_key: str | None = None
    #: How long a signed-in session lasts, and how long an invitation stays valid, in days.
    session_days: int = 30
    invitation_days: int = 7
    #: The optional mail sender. When host and sender are set, invitations and reset links are mailed
    #: (SMTP with STARTTLS; port 587 is the one the production host can reach); otherwise the link is shown to
    #: the person who issued it, and to nobody else.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str | None = None
    smtp_starttls: bool = True
    #: A CA bundle to trust for the mail server's certificate (a private relay); unset: the system's roots.
    smtp_cafile: Path | None = None
    #: The GBIF API, read for the lineage of taxon anchors (cached in the database) and for taxon names.
    gbif_api_url: str = "https://api.gbif.org/v1"
    #: The tus upload server (tusd), on loopback; nginx exposes it at /files/.
    tusd_url: str = "http://127.0.0.1:8148"
    #: Per-account upload quotas and limits (dossier 04: a whole-slide image is about 1.6 GB, so twenty fit in 40 GB).
    quota_bytes: int = 40_000_000_000
    quota_wsi: int = 20
    max_upload_bytes: int = 30_000_000_000
    #: An upload counts as a whole-slide image with a scanner extension or from this size up.
    wsi_min_bytes: int = 1_000_000_000
    #: Above this fraction of the data volume in use, whole-slide uploads are refused (the tier-A rule).
    wsi_block_fraction: float = 0.9
    #: Seconds a focal-stack fusion may run before its process is killed. The base bake, offline on a workstation,
    #: raises it: 71 planes of 53 megapixels fuse in hours.
    fuse_timeout_s: int = 7200
    #: The world basemap, a Protomaps PMTiles extract to zoom 7 (scripts/fetch_basemap.py writes it). Production
    #: nginx serves the same file; the API serves it with byte ranges when nginx is not in front (development).
    basemap: Path | None = None
    #: Windows only: the bin folder of the libvips build that includes OpenSlide. Unset on Linux.
    vips_bin: Path | None = None
    #: The local data vault with the imaging fixtures (tests only).
    fixtures: Path | None = None
    #: The tusd binary the upload tests start (tests only; production runs deploy/tusd/compose.yaml).
    tusd_bin: Path | None = None
    #: Where tests write temporary files (tests only); default ``.tmp/pytest`` in the repository.
    test_tmp: Path | None = None


    @property
    def mail_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_sender)

    @property
    def quarantine_root(self) -> Path:
        """Where tusd writes uploads until they are verified."""
        return self.data_root / "quarantine"

    @property
    def sources_root(self) -> Path:
        """Verified originals, read by processing: the files an asset's pyramid is made from."""
        return self.data_root / "sources"

    @property
    def store_root(self) -> Path:
        """The slide store: pyramid files by storage key. iipsrv reads it as its image root."""
        return self.data_root / "store"


@lru_cache
def get_settings() -> Settings:
    return Settings()
