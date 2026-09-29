"""``python -m app.worker``: run the processing worker until stopped (systemd runs it in production)."""

from __future__ import annotations

import logging
import sys

from app.worker.runner import Worker


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    worker = Worker()
    worker.install_signal_handlers()
    worker.run(max_jobs=int(argv[0]) if argv else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
