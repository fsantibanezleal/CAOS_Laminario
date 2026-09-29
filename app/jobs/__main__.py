"""Operator commands for the job queue (the deploy gate uses ``probe``).

    python -m app.jobs enqueue probe '{"steps": 3, "seconds": 2}'
    python -m app.jobs enqueue process_asset '{"asset_id": 12}' --timeout 3600
    python -m app.jobs status <public id>
    python -m app.jobs list [--limit 20]
    python -m app.jobs wait <public id> [--seconds 600]

``wait`` polls until the job ends and exits 0 when it succeeded, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from sqlalchemy import text

from app.config import Settings
from app.db.engine import database_path, make_sync_engine
from app.db.migrate import upgrade_to_head
from app.jobs import journal, kinds, queue


def _status(engine, public_id: str):
    with engine.connect() as conn:
        return conn.execute(text("SELECT id, kind, status, attempts, error, result_json FROM job "
                                 "WHERE public_id = :p"), {"p": public_id}).first()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.jobs")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("enqueue")
    add.add_argument("kind", choices=sorted(kinds.KINDS))
    add.add_argument("payload", nargs="?", default="{}")
    add.add_argument("--timeout", type=int)
    show = sub.add_parser("status")
    show.add_argument("public_id")
    listing = sub.add_parser("list")
    listing.add_argument("--limit", type=int, default=20)
    wait = sub.add_parser("wait")
    wait.add_argument("public_id")
    wait.add_argument("--seconds", type=float, default=600.0)
    args = parser.parse_args(argv)

    settings = Settings()
    upgrade_to_head(database_path(settings))
    engine = make_sync_engine(database_path(settings))
    try:
        if args.command == "enqueue":
            _, public_id = queue.enqueue(engine, args.kind, json.loads(args.payload), timeout_s=args.timeout)
            print(public_id)
            return 0
        if args.command == "list":
            with engine.connect() as conn:
                for row in conn.execute(text("SELECT public_id, kind, status, attempts, created_at FROM job "
                                             "ORDER BY id DESC LIMIT :n"), {"n": args.limit}):
                    print(f"{row.public_id}  {row.kind:14s} {row.status:10s} attempts={row.attempts} {row.created_at}")
            return 0
        deadline = time.monotonic() + (args.seconds if args.command == "wait" else 0)
        while True:
            row = _status(engine, args.public_id)
            if row is None:
                print("no such job")
                return 1
            if args.command == "status" or row.status in journal.TERMINAL or time.monotonic() > deadline:
                break
            time.sleep(1.0)
        with engine.connect() as conn:
            events = journal.after(conn, row.id, 0)
        print(f"{args.public_id} {row.kind} {row.status} attempts={row.attempts}")
        for event in events:
            print(f"  {event.seq:4d} {event.event:10s} {json.dumps(event.data)[:160]}")
        if row.error:
            print(f"  error: {row.error}")
        return 0 if row.status == "succeeded" or args.command == "status" else 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
