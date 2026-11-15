#!/usr/bin/env bash
# One-shot setup for a fresh Ubuntu 24.04 VM (2 vCPU / 4 GB RAM is plenty to start).
#
#   git clone https://github.com/aditya699/prompt-to-app.git /opt/prompt-to-app
#   sudo DOMAIN=example.com bash /opt/prompt-to-app/deploy/setup.sh   # with a domain
#   sudo bash /opt/prompt-to-app/deploy/setup.sh                      # just the VM's IP
#
# It installs Node, uv, Caddy and the sandbox tools, creates an unprivileged
# `builder` user that runs the server (and so Claude Code), builds the client,
# and starts everything with systemd. Safe to run again after a `git pull`.
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/prompt-to-app}"
APP_USER="${APP_USER:-builder}"
DOMAIN="${DOMAIN:-}"
SITES_DIR="/srv/prompt-to-app/sites"

if [[ $EUID -ne 0 ]]; then echo "Run with sudo." >&2; exit 1; fi
[[ -d "$REPO_DIR/server" ]] || { echo "Clone the repo to $REPO_DIR first." >&2; exit 1; }

echo "==> System packages"
apt-get update -y
# bubblewrap + socat: what Claude Code's sandbox uses on Linux (AGENT_SANDBOX=true).
apt-get install -y curl git ca-certificates gnupg debian-keyring debian-archive-keyring \
  apt-transport-https bubblewrap socat

if ! command -v node >/dev/null || [[ "$(node -v)" != v22* ]]; then
  echo "==> Node 22"
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

if ! command -v caddy >/dev/null; then
  echo "==> Caddy"
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y && apt-get install -y caddy
fi

echo "==> User $APP_USER"
id "$APP_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$APP_USER"
APP_HOME="$(getent passwd "$APP_USER" | cut -d: -f6)"
sudo -u "$APP_USER" bash -c 'command -v ~/.local/bin/uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh'
chown -R "$APP_USER:" "$REPO_DIR"
# Caddy serves the deployed apps from here, so it must be readable by everyone.
mkdir -p "$SITES_DIR" && chown "$APP_USER:" "$SITES_DIR" && chmod 755 "$SITES_DIR" /srv/prompt-to-app

echo "==> Server"
cd "$REPO_DIR/server"
sudo -u "$APP_USER" "$APP_HOME/.local/bin/uv" sync --no-dev --locked
if [[ ! -f .env ]]; then
  if [[ -n "$DOMAIN" ]]; then
    PUBLIC="https://app.$DOMAIN"; TEMPLATE="https://{slug}.apps.$DOMAIN"
  else
    IP="$(curl -fsS https://api.ipify.org || hostname -I | awk '{print $1}')"
    PUBLIC="http://$IP"; TEMPLATE=""
  fi
  sudo -u "$APP_USER" cp .env.example .env
  cat >> .env <<EOF

# --- Written by deploy/setup.sh ---
ENVIRONMENT=production
PUBLIC_BASE_URL=$PUBLIC
APP_URL_TEMPLATE=$TEMPLATE
CORS_ORIGINS=$PUBLIC
SITES_DIR=$SITES_DIR
WORKSPACES_DIR=$APP_HOME/workspaces
AGENT_SANDBOX=true
EOF
  echo "!! Put your ANTHROPIC_API_KEY in $REPO_DIR/server/.env, then: sudo systemctl restart prompt-to-app"
fi

echo "==> Client"
cd "$REPO_DIR/client"
sudo -u "$APP_USER" bash -c 'npm ci --no-audit --no-fund && VITE_API_URL= npm run build'
chmod -R a+rX "$REPO_DIR/client/dist"
chmod 755 "$APP_HOME" 2>/dev/null || true  # lets Caddy reach $REPO_DIR when it lives under it

echo "==> systemd"
sed -e "s#__REPO_DIR__#$REPO_DIR#g" -e "s#__APP_USER__#$APP_USER#g" -e "s#__APP_HOME__#$APP_HOME#g" \
  "$REPO_DIR/deploy/prompt-to-app.service" > /etc/systemd/system/prompt-to-app.service
systemctl daemon-reload
systemctl enable --now prompt-to-app
systemctl restart prompt-to-app

echo "==> Caddy"
if [[ -n "$DOMAIN" ]]; then
  sed -e "s#__DOMAIN__#$DOMAIN#g" -e "s#__REPO_DIR__#$REPO_DIR#g" -e "s#__SITES_DIR__#$SITES_DIR#g" \
    "$REPO_DIR/deploy/Caddyfile.domain" > /etc/caddy/Caddyfile
else
  sed -e "s#__REPO_DIR__#$REPO_DIR#g" "$REPO_DIR/deploy/Caddyfile.ip" > /etc/caddy/Caddyfile
fi
systemctl reload caddy || systemctl restart caddy

echo
if [[ -n "$DOMAIN" ]]; then
  echo "Done. Open https://app.$DOMAIN (DNS: app.$DOMAIN and *.apps.$DOMAIN -> this VM)."
else
  echo "Done. Open http://<this VM's IP>/"
fi
