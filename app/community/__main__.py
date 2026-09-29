"""``python -m app.community backfill``: every published slide gets its first identification and its badge.

Idempotent; run after migration 0011 on a database that already holds slides (the deploy runbook does), and by the
base import after it loads a bake. It reads taxon lineages from the cache only.
"""

from __future__ import annotations

import argparse
import sys

from app.community import store
from app.config import get_settings
from app.db.engine import database_path, make_sync_engine
from app.db.migrate import upgrade_to_head


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.community")
    sub = parser.add_subparsers(dest="step", required=True)
    sub.add_parser("backfill", help="the first identification and the badge of every published slide")
    parser.parse_args(argv)
    settings = get_settings()
    database = database_path(settings)
    upgrade_to_head(database)
    engine = make_sync_engine(database)
    try:
        with engine.begin() as conn:
            counts = store.backfill(conn)
    finally:
        engine.dispose()
    print(f"{counts['slides']} published slides; {counts['identifications']} first identifications made")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
