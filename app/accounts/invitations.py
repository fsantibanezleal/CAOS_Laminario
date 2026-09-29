"""Invitations: the only way to an account.

An invitation is a random 32-byte token in a link, valid ``invitation_days``, usable once. Only its SHA-256 is
stored. Registration claims it with one conditional ``UPDATE`` (unused, not revoked, not expired), so two
registrations racing with the same link cannot both succeed; if the account then cannot be created (the email
already has one), the claim is released.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models import Invitation, User

TOKEN_BYTES = 32


def digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def status(invitation: Invitation, now: datetime | None = None) -> str:
    now = now or utcnow()
    if invitation.revoked_at:
        return "revoked"
    if invitation.used_at:
        return "used"
    if invitation.expires_at <= now:
        return "expired"
    return "pending"


async def issue(db: AsyncSession, *, role: str, days: int, email: str | None, issued_by, note: str | None
                ) -> tuple[Invitation, str]:
    """A new invitation and its token (the token exists only in the returned link)."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    invitation = Invitation(token_sha256=digest(token), email=email.lower() if email else None, role=role,
                            issued_by_id=issued_by, note=note, expires_at=utcnow() + timedelta(days=days))
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation, token


async def claim(db: AsyncSession, token: str) -> Invitation | None:
    """Mark the invitation of ``token`` used, if it can be; None when it is unknown, used, revoked or expired."""
    now = utcnow()
    result = await db.execute(
        update(Invitation)
        .where(Invitation.token_sha256 == digest(token), Invitation.used_at.is_(None),
               Invitation.revoked_at.is_(None), Invitation.expires_at > now)
        .values(used_at=now)
    )
    await db.commit()
    if result.rowcount != 1:
        return None
    return (await db.execute(select(Invitation).where(Invitation.token_sha256 == digest(token)))).scalar_one()


async def release(db: AsyncSession, invitation_id: int) -> None:
    await db.execute(update(Invitation).where(Invitation.id == invitation_id).values(used_at=None, used_by_id=None))
    await db.commit()


async def mark_used_by(db: AsyncSession, invitation_id: int, user_id) -> None:
    await db.execute(update(Invitation).where(Invitation.id == invitation_id).values(used_by_id=user_id))
    await db.commit()


async def count_admins(db: AsyncSession) -> int:
    query = select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))
    return (await db.execute(query)).scalar_one()
