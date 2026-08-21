#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/console-gg}"
SERVICE="console-gg-ttyd.service"

sudo chmod 0755 "$APP_DIR/deploy/linux/start-ttyd.sh"
sudo cp "$APP_DIR/deploy/linux/console-gg-ttyd.service" /etc/systemd/system/console-gg-ttyd.service
sudo systemctl daemon-reload
sudo systemctl reset-failed console-gg-ttyd.service || true
sudo systemctl enable --now console-gg-ttyd.service

echo
echo "Console GG e abilitato al boot."
sudo systemctl is-enabled "$SERVICE"
sudo systemctl is-active "$SERVICE"
sudo systemctl status "$SERVICE" --no-pager -l
