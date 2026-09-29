"""fastapi-users wired for Laminario (ADR-0044): accounts in the app's own database, sessions in a cookie.

- **Sessions** are opaque tokens in an ``HttpOnly`` cookie (``Secure`` in production, ``SameSite=Lax``), each a row
  of ``accesstoken`` that sign-out deletes (fastapi-users' database strategy), valid ``session_days``.
- **Passwords** are hashed by fastapi-users (pwdlib, Argon2) and must have at least 12 characters and not contain
  the email's local part.
- **Password reset**: fastapi-users signs a one-hour token with ``secret_key``. The link is mailed when a sender is
  configured; otherwise an admin issues it for the person (``POST /api/admin/accounts/{id}/reset-link``) and it is
  shown to that admin only.
- **There is no open registration**: the fastapi-users register route is not mounted; accounts come from
  invitations (``app/accounts/invitations.py``).

Everything that depends on the settings (cookie flags, lifetimes, the secret) is built per application by
``build``, so tests and production each get their own.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi_users import BaseUserManager, FastAPIUsers, InvalidPasswordException, UUIDIDMixin, schemas
from fastapi_users.authentication import AuthenticationBackend, CookieTransport
from fastapi_users.authentication.strategy.db import DatabaseStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import mail
from app.config import Settings
from app.db.models import AccessToken, User
from app.db.session import session

MIN_PASSWORD_LENGTH = 12
COOKIE_NAME = "laminario_session"
RESET_LIFETIME_SECONDS = 3600


class UserRead(schemas.BaseUser[uuid.UUID]):
    role: str
    display_name: str


class UserCreate(schemas.BaseUserCreate):
    display_name: str = Field(min_length=1, max_length=80)
    role: str = "contributor"


class UserUpdate(schemas.BaseUserUpdate):
    """What an account may change about itself: never its role."""

    display_name: str | None = Field(None, min_length=1, max_length=80)


@lru_cache
def _process_secret() -> str:
    return secrets.token_urlsafe(48)


def secret_key(settings: Settings) -> str:
    if settings.secret_key:
        return settings.secret_key
    if settings.env == "production":
        raise RuntimeError("LAMINARIO_SECRET_KEY must be set in production")
    return _process_secret()


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_lifetime_seconds = RESET_LIFETIME_SECONDS

    def __init__(self, user_db, settings: Settings):
        super().__init__(user_db)
        self.settings = settings
        self.reset_password_token_secret = secret_key(settings)
        self.verification_token_secret = secret_key(settings)

    async def validate_password(self, password: str, user) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordException(reason=f"the password needs at least {MIN_PASSWORD_LENGTH} characters")
        local = str(user.email).split("@", 1)[0].lower()
        if len(local) >= 4 and local in password.lower():
            raise InvalidPasswordException(reason="the password must not contain the email address")

    async def on_after_forgot_password(self, user: User, token: str, request: Request | None = None) -> None:
        link = f"{self.settings.public_base_url.rstrip('/')}/reset-password?token={token}"
        if request is not None and getattr(request.state, "capture_reset_link", False):
            request.state.reset_link = link  # an admin asked for it: shown to that admin only
        elif self.settings.mail_configured:
            message = mail.reset_message(self.settings, user.email, link, RESET_LIFETIME_SECONDS // 60)
            await run_in_threadpool(mail.send, self.settings, message)


async def get_user_db(db: Annotated[AsyncSession, Depends(session)]):
    yield SQLAlchemyUserDatabase(db, User)


async def get_access_token_db(db: Annotated[AsyncSession, Depends(session)]):
    yield SQLAlchemyAccessTokenDatabase(db, AccessToken)


async def get_user_manager(request: Request, user_db: Annotated[object, Depends(get_user_db)]):
    yield UserManager(user_db, request.app.state.settings)


@dataclass
class Accounts:
    """The fastapi-users objects of one application."""

    users: FastAPIUsers
    backend: AuthenticationBackend

    @property
    def current(self):
        return self.users.current_user(active=True)

    @property
    def optional(self):
        return self.users.current_user(active=True, optional=True)


def build(settings: Settings) -> Accounts:
    lifetime = settings.session_days * 24 * 3600
    transport = CookieTransport(cookie_name=COOKIE_NAME, cookie_max_age=lifetime,
                                cookie_secure=settings.env == "production", cookie_httponly=True,
                                cookie_samesite="lax")

    def strategy(access_token_db: Annotated[object, Depends(get_access_token_db)]) -> DatabaseStrategy:
        return DatabaseStrategy(access_token_db, lifetime_seconds=lifetime)

    backend = AuthenticationBackend(name="cookie", transport=transport, get_strategy=strategy)
    return Accounts(users=FastAPIUsers[User, uuid.UUID](get_user_manager, [backend]), backend=backend)
