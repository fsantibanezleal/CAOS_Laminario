"""Roles and what each may do.

Visitors need no account: every published slide, its images and its manifest are public. Accounts carry one
role; each role includes everything the roles below it may do:

| Role | Adds |
|---|---|
| contributor | submit slide cases (drafts of their own) |
| identifier | propose and support identifications on any slide (U13) |
| curator | moderate (hide, restore, verify), override a placement with a reason, invite up to identifier |
| admin | manage invitations and accounts, issue invitations for any role |

``CAPABILITIES`` is the single table the routes check (``require``); the role-matrix gate walks it.
"""

from __future__ import annotations

from typing import Literal

Role = Literal["contributor", "identifier", "curator", "admin"]
ROLES: tuple[Role, ...] = ("contributor", "identifier", "curator", "admin")
RANK = {role: rank for rank, role in enumerate(ROLES, start=1)}

#: capability -> the lowest role that has it (None: visitors too)
CAPABILITIES: dict[str, Role | None] = {
    "read": None,
    "submit": "contributor",
    "identify": "identifier",
    "moderate": "curator",
    "override_placement": "curator",
    "invite": "curator",
    "manage_invitations": "admin",
    "manage_accounts": "admin",
}

#: The highest role each role may invite.
INVITES_UP_TO: dict[Role, Role | None] = {"contributor": None, "identifier": None, "curator": "identifier",
                                          "admin": "admin"}


def allowed(role: str | None, capability: str) -> bool:
    """Whether an account with ``role`` (None for a visitor) has ``capability``."""
    needed = CAPABILITIES[capability]
    if needed is None:
        return True
    return role is not None and RANK.get(role, 0) >= RANK[needed]


def may_invite(issuer_role: str, invited_role: str) -> bool:
    ceiling = INVITES_UP_TO.get(issuer_role)  # type: ignore[arg-type]
    return ceiling is not None and invited_role in RANK and RANK[invited_role] <= RANK[ceiling]
