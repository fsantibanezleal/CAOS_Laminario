#!/usr/bin/env bash
# Install or update Laminario on the production host (U16), run as root on hetzner-ml-fasl-work:
#
#   bash deploy/install.sh [REF]          (REF: a tag or branch of the repository, main by default)
#
# Every step is idempotent. It creates the laminario account and the folders of the data root on the volume, puts the
# code at REF in /opt/fasl-apps/CAOS_Laminario with its virtual environment and web build, migrates the database, and
# installs the nginx site once the certificate exists. It does not register the long-running services: that is
# deploy/register-services.sh, a person's step. When the services are registered, it restarts them on the new code.
#
# Needs /etc/fasl-laminario.env (deploy/fasl-laminario.env.example lists its settings; the values are in the vault).
set -euo pipefail

REF="${1:-main}"
REPO=/opt/fasl-apps/CAOS_Laminario
DATA=/srv/laminario
DOMAIN=laminario.ml.fasl-work.com
ENV_FILE=/etc/fasl-laminario.env

test -f "$ENV_FILE" || { echo "missing $ENV_FILE (see deploy/fasl-laminario.env.example)" >&2; exit 1; }
mountpoint -q "$DATA" || { echo "$DATA is not mounted (the laminario-data volume)" >&2; exit 1; }

# 1. The account the API and the worker run as, and the data root's folders.
id laminario >/dev/null 2>&1 || useradd --system --home-dir "$DATA" --no-create-home --shell /usr/sbin/nologin laminario
install -d -o laminario -g laminario -m 0755 "$DATA" "$DATA/store" "$DATA/sources" "$DATA/quarantine" "$DATA/basemap" \
  "$DATA/bake"
# nginx writes its tile and access caches.
install -d -o www-data -g www-data -m 0750 "$DATA/cache" "$DATA/cache/tiles" "$DATA/cache/access"
chown root:laminario "$ENV_FILE" && chmod 0640 "$ENV_FILE"

# 2. The code at REF.
if [ ! -d "$REPO/.git" ]; then
  git clone --quiet https://github.com/fsantibanezleal/CAOS_Laminario.git "$REPO"
fi
git -C "$REPO" fetch --quiet --tags origin
git -C "$REPO" checkout --quiet --detach "origin/$REF" 2>/dev/null || git -C "$REPO" checkout --quiet --detach "$REF"
echo "code at $(git -C "$REPO" describe --tags --always) ($(git -C "$REPO" rev-parse --short HEAD))"

# 3. The server's Python environment (libvips42t64 comes from Ubuntu).
test -x "$REPO/.venv/bin/python" || python3.12 -m venv "$REPO/.venv"
"$REPO/.venv/bin/pip" install --quiet --upgrade pip
"$REPO/.venv/bin/pip" install --quiet -r "$REPO/requirements-api.txt"

# 4. The web app.
(cd "$REPO/frontend" && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci --no-audit --no-fund --loglevel=error \
  && npm run build --silent)

# 5. The database, as the service account, with the service's settings.
set -a; . "$ENV_FILE"; set +a
(cd "$REPO" && runuser -u laminario --preserve-environment -- "$REPO/.venv/bin/python" -m app.db.migrate)

# 6. The certificate (certbot's nginx authenticator, which leaves the site files alone), then the site.
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  certbot certonly --nginx -d "$DOMAIN" --non-interactive --keep-until-expiring
fi
install -m 0644 "$REPO/deploy/nginx/laminario.conf" /etc/nginx/sites-available/laminario.conf
ln -sf ../sites-available/laminario.conf /etc/nginx/sites-enabled/laminario.conf
# A site that fails the test must not stay enabled: the next reload of any site on the host would fail on it.
if ! nginx -t; then
  rm -f /etc/nginx/sites-enabled/laminario.conf
  echo "the nginx site failed its test and was disabled again" >&2
  exit 1
fi
systemctl reload nginx

# 7. The services, when they are registered, on the new code.
for unit in fasl-laminario fasl-laminario-worker; do
  if systemctl is-enabled --quiet "$unit" 2>/dev/null; then
    systemctl restart "$unit"
    echo "restarted $unit"
  else
    echo "$unit is not registered yet: run deploy/register-services.sh"
  fi
done
echo "installed $(cat "$REPO/VERSION")"
