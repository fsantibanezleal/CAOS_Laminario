"""Accounts: sign-in and sign-out, invitation-only registration, invitations, admin actions, contributing.

Built per application (``routers``) because the fastapi-users objects depend on the settings.

| Route | Who |
|---|---|
| `POST /api/auth/login`, `POST /api/auth/logout` | anyone with an account (fastapi-users; a session cookie) |
| `POST /api/auth/register` | anyone holding a valid invitation link |
| `POST /api/auth/forgot-password`, `POST /api/auth/reset-password` | anyone; mailed only when mail is configured |
| `GET/PATCH /api/users/me` | the account itself (never its role) |
| `GET /api/session` | anyone: the signed-in account, or null |
| `POST/GET /api/invitations`, `DELETE /api/invitations/{id}` | curators (own, up to identifier), admins (all) |
| `POST /api/admin/accounts/{id}/reset-link`, `PATCH /api/admin/accounts/{id}/role` | admins |
| `POST /api/slide-cases` | contributors and above; a placement override needs a curator |
"""

# No ``from __future__ import annotations`` here: the dependency aliases are defined inside ``routers`` and FastAPI
# must see them as objects, not as names to resolve later.
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi_users import exceptions as fu_exceptions
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounts import handles, invitations, mail, roles
from app.accounts.users import Accounts, UserCreate, UserRead, UserUpdate, get_user_manager
from app.collections import taxa
from app.collections.service import check_submission
from app.contracts import catalog as c
from app.contracts.ingest import validate_submission
from app.db.models import Invitation, User
from app.db.session import session
from app.services import slides


class Registration(BaseModel):
    token: str = Field(min_length=20, max_length=100)
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)


class InvitationRequest(BaseModel):
    role: roles.Role = "contributor"
    email: EmailStr | None = None
    note: str | None = Field(None, max_length=200)


class RoleChange(BaseModel):
    role: roles.Role


def _refused(code: str, reason: str) -> HTTPException:
    """A refused registration, shaped as fastapi-users shapes its own (a code the interface words, and the reason)."""
    return HTTPException(status_code=400, detail={"code": code, "reason": reason})


def account_record(user: User) -> c.AccountRecord:
    return c.AccountRecord(id=str(user.id), email=user.email, display_name=user.display_name, role=user.role,
                           is_active=user.is_active, is_verified=user.is_verified, handle=user.handle)


def invitation_record(invitation: Invitation, link: str | None = None) -> c.InvitationRecord:
    return c.InvitationRecord(id=invitation.id, email=invitation.email, role=invitation.role, note=invitation.note,
                              status=invitations.status(invitation), created_at=invitation.created_at,
                              expires_at=invitation.expires_at, mailed=invitation.mailed, link=link)


def requirement(accounts: Accounts, capability: str):
    """A dependency that returns the signed-in account when its role has ``capability``, else 403."""

    async def dependency(user: Annotated[User, Depends(accounts.current)]) -> User:
        if not roles.allowed(user.role, capability):
            raise HTTPException(status_code=403, detail=f"the {user.role} role cannot {capability.replace('_', ' ')}")
        return user

    return dependency


def routers(accounts: Accounts) -> list[APIRouter]:
    fu = accounts.users
    auth = APIRouter(prefix="/api/auth", tags=["accounts"])
    auth.include_router(fu.get_auth_router(accounts.backend))
    auth.include_router(fu.get_reset_password_router())
    users = APIRouter(prefix="/api/users", tags=["accounts"])
    users.include_router(fu.get_users_router(UserRead, UserUpdate))
    api = APIRouter(tags=["accounts"])
    Db = Annotated[AsyncSession, Depends(session)]
    Inviter = Annotated[User, Depends(requirement(accounts, "invite"))]
    Admin = Annotated[User, Depends(requirement(accounts, "manage_accounts"))]
    Contributor = Annotated[User, Depends(requirement(accounts, "submit"))]
    Manager = Annotated[Any, Depends(get_user_manager)]
    Reader = Annotated[User | None, Depends(accounts.optional)]

    @api.get("/api/session", response_model=c.AccountRecord | None)
    async def session_account(reader: Reader) -> c.AccountRecord | None:
        """The signed-in account, or null for a visitor: a 200 either way, since a visitor is not an error."""
        return account_record(reader) if reader is not None else None

    @auth.post("/register", status_code=201, response_model=c.AccountRecord)
    async def register(payload: Registration, db: Db, manager: Manager) -> c.AccountRecord:
        """Create an account with an invitation link: valid, unexpired, unused, and for this email if it names one."""
        claimed = await invitations.claim(db, payload.token)
        if claimed is None:
            raise _refused("REGISTER_INVITATION_INVALID",
                           "this invitation is not valid: unknown, used, revoked or expired")
        if claimed.email and claimed.email != payload.email.lower():
            await invitations.release(db, claimed.id)
            raise _refused("REGISTER_INVITATION_OTHER_EMAIL", "this invitation is for another email address")
        try:
            user = await manager.create(UserCreate(email=payload.email, password=payload.password,
                                                   display_name=payload.display_name, role=claimed.role,
                                                   is_superuser=claimed.role == "admin", is_verified=True),
                                        safe=False)
        except fu_exceptions.UserAlreadyExists as exc:
            await invitations.release(db, claimed.id)
            raise _refused("REGISTER_USER_ALREADY_EXISTS", "an account with this email already exists") from exc
        except fu_exceptions.InvalidPasswordException as exc:
            await invitations.release(db, claimed.id)
            raise _refused("REGISTER_INVALID_PASSWORD", str(exc.reason)) from exc
        await invitations.mark_used_by(db, claimed.id, user.id)
        # The profile's public address (U14): made from the display name, unique.
        row = await db.get(User, user.id)
        row.handle = await handles.free_handle(db, row.display_name)
        await db.commit()
        return account_record(row)

    @api.post("/api/invitations", status_code=201, response_model=c.InvitationRecord)
    async def create_invitation(payload: InvitationRequest, request: Request, db: Db,
                                issuer: Inviter) -> c.InvitationRecord:
        """Issue an invitation. Without a mail sender (or an email) the link is in this answer, and only here."""
        if not roles.may_invite(issuer.role, payload.role):
            raise HTTPException(status_code=403, detail=f"a {issuer.role} cannot invite a {payload.role}")
        settings = request.app.state.settings
        invitation, token = await invitations.issue(db, role=payload.role, days=settings.invitation_days,
                                                    email=payload.email, issued_by=issuer.id, note=payload.note)
        link = f"{settings.public_base_url.rstrip('/')}/join?token={token}"
        if settings.mail_configured and payload.email:
            message = mail.invitation_message(settings, payload.email, link, payload.role, settings.invitation_days)
            await run_in_threadpool(mail.send, settings, message)
            invitation.mailed = True
            await db.commit()
            return invitation_record(invitation)
        return invitation_record(invitation, link=link)

    @api.get("/api/invitations", response_model=list[c.InvitationRecord])
    async def list_invitations(db: Db, issuer: Inviter) -> list[c.InvitationRecord]:
        query = select(Invitation).order_by(Invitation.id.desc())
        if not roles.allowed(issuer.role, "manage_invitations"):
            query = query.where(Invitation.issued_by_id == issuer.id)
        return [invitation_record(i) for i in (await db.execute(query)).scalars()]

    @api.delete("/api/invitations/{invitation_id}", status_code=204)
    async def revoke_invitation(invitation_id: int, db: Db, issuer: Inviter) -> Response:
        invitation = await db.get(Invitation, invitation_id)
        own = invitation is not None and invitation.issued_by_id == issuer.id
        if invitation is None or not (own or roles.allowed(issuer.role, "manage_invitations")):
            raise HTTPException(status_code=404, detail="no such invitation of yours")
        if invitation.used_at is None and invitation.revoked_at is None:
            from app.db.base import utcnow

            invitation.revoked_at = utcnow()
            await db.commit()
        return Response(status_code=204)

    @api.post("/api/admin/accounts/{user_id}/reset-link")
    async def reset_link(user_id: uuid.UUID, request: Request, admin: Admin, manager: Manager) -> dict[str, Any]:
        """A password-reset link for someone who cannot receive mail, shown to the admin who asked."""
        try:
            user = await manager.get(user_id)
        except fu_exceptions.UserNotExists as exc:
            raise HTTPException(status_code=404, detail="no such account") from exc
        request.state.capture_reset_link = True
        await manager.forgot_password(user, request)
        minutes = manager.reset_password_token_lifetime_seconds // 60
        return {"link": request.state.reset_link, "expires_in_minutes": minutes}

    @api.patch("/api/admin/accounts/{user_id}/role", response_model=c.AccountRecord)
    async def change_role(user_id: uuid.UUID, payload: RoleChange, db: Db, admin: Admin) -> c.AccountRecord:
        user = await db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="no such account")
        if user.role == "admin" and payload.role != "admin" and await invitations.count_admins(db) <= 1:
            raise HTTPException(status_code=409, detail="the last admin cannot lose the role")
        user.role = payload.role
        user.is_superuser = payload.role == "admin"
        await db.commit()
        return account_record(user)

    @api.post("/api/slide-cases", status_code=201, response_model=c.CreatedSlideCase,
              responses={422: {"model": c.ValidationResult}})
    async def create_slide_case(payload: Annotated[Any, Body()], request: Request, db: Db, contributor: Contributor):
        """Store a slide case as a draft of the signed-in contributor (images arrive through uploads, U5)."""
        report = validate_submission(payload)
        if not report.valid:
            return JSONResponse(status_code=422, content=c.ValidationResult(valid=False, errors=report.errors)
                                .model_dump())
        submission = report.submission
        if submission.placement.override_reason and not roles.allowed(contributor.role, "override_placement"):
            raise HTTPException(status_code=403, detail="only a curator can override a placement")
        if submission.origin == "base" and not roles.allowed(contributor.role, "manage_accounts"):
            raise HTTPException(status_code=403, detail="base-collection cases come from the import, not from a person")
        try:
            checked = await check_submission(db, request.app.state.gbif_client, submission)
        except taxa.TaxonServiceUnavailable as exc:
            raise HTTPException(status_code=503, detail=f"the GBIF taxonomy did not answer; try again ({exc})") from exc
        if checked.errors:
            await db.commit()  # keep the taxa just cached
            return JSONResponse(status_code=422, content=c.ValidationResult(valid=False, errors=checked.errors)
                                .model_dump())
        slide = await slides.create_slide(db, submission, contributor_id=str(contributor.id),
                                          resolved=checked.anchor)
        return c.CreatedSlideCase(id=slide.short_id, status=slide.status, flags=report.flags)

    return [auth, users, api]
