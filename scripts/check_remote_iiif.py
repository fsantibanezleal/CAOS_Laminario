#!/usr/bin/env python3
"""The link check: re-read every remote IIIF asset and report where it no longer meets the contract.

Reads the database under ``LAMINARIO_DATA_ROOT`` (or ``.env``), applies the remote-asset contract of
``app/delivery/remote.py`` to each remote asset with the dimensions and licence recorded for it, and prints one
line per asset. Nothing is changed: a source that altered its record is reported for a person to decide.

Usage: ``python scripts/check_remote_iiif.py [--origin https://laminario.ml.fasl-work.com]``
Exit status: 0 when every remote asset passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx2  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.contracts import licences  # noqa: E402
from app.db.engine import database_path, make_sync_engine  # noqa: E402
from app.db.models import Asset, Slide  # noqa: E402
from app.delivery.remote import TIMEOUT_SECONDS, check_remote_asset  # noqa: E402


def main(argv: list[str]) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--origin", default=settings.public_base_url.rstrip("/"),
                        help="the browser origin the services must allow (default: the public base URL)")
    args = parser.parse_args(argv)
    engine = make_sync_engine(database_path(settings))
    failures = checked = 0
    with Session(engine) as db, httpx2.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
        rows = db.execute(
            select(Asset, Slide).join(Slide, Asset.slide_id == Slide.id).where(Asset.media_kind == "remote_iiif")
        ).all()
        for asset, slide in rows:
            checked += 1
            result = check_remote_asset(asset.remote_info_url or "", width=asset.width_px or 0,
                                        height=asset.height_px or 0, origin=slide.origin,
                                        request_origin=args.origin, client=client)
            recorded = licences.canonical(asset.licence_uri)
            if result.ok and result.licence_uri != recorded:
                print(f"CHANGED {slide.short_id} asset {asset.id}: licence {recorded} is now {result.licence_uri}")
                failures += 1
            elif result.ok:
                print(f"ok      {slide.short_id} asset {asset.id}: {asset.remote_info_url}")
            else:
                failures += 1
                for problem in result.problems:
                    print(f"FAIL    {slide.short_id} asset {asset.id}: {problem.field}: {problem.message} "
                          f"(expected {problem.expected})")
    engine.dispose()
    print(f"{checked} remote asset(s) checked, {failures} with problems")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
