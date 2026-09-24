#!/usr/bin/env bash
# Laminario, step 1: one-stop setup from a fresh clone. Idempotent; --force rebuilds the venv.
#
#   ./scripts/local/01_init.sh
#   ./scripts/local/01_init.sh --force
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

force=0
if [ "${1:-}" = "--force" ]; then force=1; fi

echo
echo "Laminario init"
echo

py=""
for cand in python3.12 python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" --version 2>&1 | grep -q "3\.12"; then py="$cand"; break; fi
done
if [ -z "$py" ]; then echo "Python 3.12 is required. Run: ./scripts/local/00_install-prereqs.sh"; exit 1; fi
echo "  [1/3] $("$py" --version)"

if [ "$force" -eq 1 ]; then rm -rf .venv; fi
if [ ! -d .venv ]; then "$py" -m venv .venv; fi
if [ -x .venv/bin/python ]; then vpy=.venv/bin/python; else vpy=.venv/Scripts/python.exe; fi
"$vpy" -m pip install --upgrade pip -q
"$vpy" -m pip install -q -r requirements-dev.txt
echo "  [2/3] .venv ready"

# Secrets never live in this repository. LAMINARIO_ENV_SOURCE may name a working env file.
if [ ! -f .env ]; then
  if [ -n "${LAMINARIO_ENV_SOURCE:-}" ] && [ -f "$LAMINARIO_ENV_SOURCE" ]; then
    cp "$LAMINARIO_ENV_SOURCE" .env
    echo "  [3/3] .env copied from LAMINARIO_ENV_SOURCE"
  else
    cp .env.example .env
    echo "  [3/3] .env created from .env.example (local defaults)"
  fi
else
  echo "  [3/3] .env already present, left as it is"
fi

echo
echo "  Ready. Tests:  $vpy -m pytest"
echo "  Next:         ./scripts/local/03_dev.sh"
echo
