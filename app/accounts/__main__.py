"""Operator commands for accounts, run on the server.

    python -m app.accounts invite --role admin [--email person@example.org] [--note "first admin"]

Issues an invitation without an issuing account and prints its link. This is how the first admin is created: whoever
can run commands on the server can already do anything, so the command line is the trust root. Every later
invitation comes from a curator or an admin in the app.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.accounts import invitations, roles
from app.config import Settings
from app.db.engine import async_sessions, database_path, make_async_engine
from app.db.migrate import upgrade_to_head


async def invite(settings: Settings, role: str, email: str | None, note: str | None) -> str:
    upgrade_to_head(database_path(settings))
    engine = make_async_engine(database_path(settings))
    try:
        async with async_sessions(engine)() as db:
            _, token = await invitations.issue(db, role=role, days=settings.invitation_days, email=email,
                                               issued_by=None, note=note)
    finally:
        await engine.dispose()
    return f"{settings.public_base_url.rstrip('/')}/join?token={token}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.accounts")
    sub = parser.add_subparsers(dest="command", required=True)
    issue = sub.add_parser("invite", help="issue an invitation link from the server's command line")
    issue.add_argument("--role", choices=roles.ROLES, default="admin")
    issue.add_argument("--email")
    issue.add_argument("--note", default="issued from the command line")
    args = parser.parse_args(argv)
    settings = Settings()
    link = asyncio.run(invite(settings, args.role, args.email, args.note))
    print(link)
    print(f"valid for {settings.invitation_days} days, once", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
