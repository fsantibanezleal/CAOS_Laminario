#!/usr/bin/env bash
# Laminario, step 3: run the API locally with auto-reload.
#
#   ./scripts/local/03_dev.sh [port]
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."
port="${1:-8147}"
if [ -x .venv/bin/python ]; then
  vpy=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then
  vpy=.venv/Scripts/python.exe
else
  echo "No .venv yet. Run: ./scripts/local/01_init.sh"
  exit 1
fi
# Refuse a port someone else already holds: a gate that reuses a listening port tests another product.
if command -v ss >/dev/null 2>&1 && ss -ltn | grep -q ":$port "; then
  echo "Port $port is already in use. Pass another port."
  exit 1
fi
echo "Laminario API on http://127.0.0.1:$port  (health: /api/health, docs: /api/docs)"
exec "$vpy" -m uvicorn app.main:app --reload --host 127.0.0.1 --port "$port"
