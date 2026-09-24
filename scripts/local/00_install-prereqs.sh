#!/usr/bin/env bash
# Laminario, step 0: system-level prerequisites (Linux, macOS, Git Bash).
# Checks and reports; it does not install system software. Same checks as the PowerShell version.
#
#   ./scripts/local/00_install-prereqs.sh
set -Eeuo pipefail

missing=0
echo
echo "Laminario prerequisites"
echo

py=""
for cand in python3.12 python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    v="$("$cand" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)"
    if [ "$v" = "3.12" ]; then py="$cand"; break; fi
  fi
done
if [ -n "$py" ]; then echo "  Python 3.12 ($py)"; else echo "  Python 3.12 not found"; missing=1; fi

if command -v node >/dev/null 2>&1; then
  nv="$(node --version | grep -oE '[0-9]+' | head -1)"
  if [ "$nv" -ge 22 ] && [ "$nv" -lt 25 ]; then echo "  Node $(node --version)"; else echo "  Node 22 to 24 needed (found $(node --version))"; missing=1; fi
else
  echo "  Node not found"; missing=1
fi

if command -v git >/dev/null 2>&1; then echo "  $(git --version)"; else echo "  git not found"; missing=1; fi
if command -v docker >/dev/null 2>&1; then echo "  $(docker --version)"; else echo "  Docker not found (needed for the local tile server)"; fi

echo
if [ "$missing" -ne 0 ]; then
  echo "  Missing prerequisites: install them with your package manager, then re-run."
  exit 1
fi
echo "  Ready. Next:  ./scripts/local/01_init.sh"
echo
