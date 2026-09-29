#!/usr/bin/env bash
# Register and start Laminario's long-running services on the production host (U16). A person's step: the management
# rules keep the registration of services that outlive a session out of automated runs. Run once, as root, after
# deploy/install.sh:
#
#   bash /opt/fasl-apps/CAOS_Laminario/deploy/register-services.sh
#
# It installs the API and worker units, enables and starts them, and starts tusd and iipsrv from their pinned images
# (restart unless stopped). Later updates need only deploy/install.sh, which restarts the registered services.
set -euo pipefail

REPO=/opt/fasl-apps/CAOS_Laminario
cd "$REPO"

install -m 0644 deploy/systemd/fasl-laminario.service deploy/systemd/fasl-laminario-worker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now fasl-laminario.service fasl-laminario-worker.service

LAMINARIO_UID="$(id -u laminario)" LAMINARIO_GID="$(id -g laminario)" docker compose -f deploy/tusd/compose.yaml up -d
LAMINARIO_STORE=/srv/laminario/store docker compose -f deploy/iipsrv/compose.yaml up -d

# The API answers once uvicorn has imported the app and opened the database: up to 30 s.
for _ in $(seq 1 30); do
  curl -fsS -o /dev/null http://127.0.0.1:8147/api/health 2>/dev/null && break
  sleep 1
done
curl -fsS http://127.0.0.1:8147/api/health && echo
curl -fsS -o /dev/null -w "tusd %{http_code}\n" -X OPTIONS http://127.0.0.1:8148/files/
curl -fsS -o /dev/null -w "iipsrv %{http_code}\n" http://127.0.0.1:8149/ || true
systemctl --no-pager --lines=0 status fasl-laminario.service fasl-laminario-worker.service
