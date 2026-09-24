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


@lru_cache
def get_settings() -> Settings:
    return Settings()
