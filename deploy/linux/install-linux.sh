#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/console-gg}"
STATE_DIR="${STATE_DIR:-/var/lib/console-gg}"
SERVICE_USER="${SERVICE_USER:-consolegg}"
ENV_DIR="${ENV_DIR:-/etc/console-gg}"
# Default env file: /etc/console-gg/console-gg.env.
ENV_FILE="$ENV_DIR/console-gg.env"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip rsync ttyd

if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  sudo useradd --system --home "$STATE_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

sudo mkdir -p "$APP_DIR" "$STATE_DIR"
sudo install -m 0755 -d "$ENV_DIR"
if [ ! -f "$ENV_FILE" ]; then
  printf '%s\n' \
    '# Optional LAN gate for native ttyd. Format: username:password' \
    '# CONSOLE_GG_TTYD_CREDENTIAL=arcade:change-me' |
    sudo tee "$ENV_FILE" >/dev/null
  sudo chmod 600 "$ENV_FILE"
fi

sudo rsync -a --delete \
  --exclude ".git" \
  --exclude ".agents" \
  --exclude ".codex" \
  --exclude ".superpowers" \
  --exclude ".venv" \
  --exclude "node_modules" \
  --exclude "winner_bot" \
  --exclude "tests/test_winner_bot_*.py" \
  --exclude "docs/superpowers" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude "console_gg_stats.json" \
  "$REPO_DIR"/ "$APP_DIR"/

sudo chown -R root:root "$APP_DIR"
sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$STATE_DIR"

sudo python3 -m venv "$APP_DIR/.venv"
sudo "$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
sudo "$APP_DIR/.venv/bin/python" -m pip install -e "$APP_DIR"

sudo chmod 0755 "$APP_DIR/deploy/linux/start-ttyd.sh"
sudo cp "$APP_DIR/deploy/linux/console-gg-ttyd.service" /etc/systemd/system/console-gg-ttyd.service
sudo systemctl daemon-reload
sudo systemctl reset-failed console-gg-ttyd.service || true
sudo systemctl enable --now console-gg-ttyd.service
sudo systemctl restart console-gg-ttyd.service
sudo systemctl is-enabled console-gg-ttyd.service
sudo systemctl is-active console-gg-ttyd.service

echo "Console GG attivo su http://<IP_VM>:7681"
echo "Login opzionale ttyd: sudo nano $ENV_FILE"
echo "Diagnostica: bash deploy/linux/diagnose-linux.sh"
