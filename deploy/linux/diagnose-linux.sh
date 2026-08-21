#!/usr/bin/env bash
set -u

SERVICE="console-gg-ttyd.service"
PORT="${PORT:-7681}"

section() {
  echo
  echo "=== $1 ==="
}

section "Servizio"
systemctl is-enabled console-gg-ttyd.service || true
systemctl is-active console-gg-ttyd.service || true
systemctl status console-gg-ttyd.service --no-pager -l || true

section "Log del boot corrente"
journalctl -u console-gg-ttyd.service -b --no-pager -n 80 || true

section "Porta ${PORT}"
ss -ltnp "sport = :${PORT}" || sudo ss -ltnp "sport = :${PORT}" || true

section "IP della VM"
hostname -I || true
ip -4 addr show scope global || true

section "Firewall"
if command -v ufw >/dev/null 2>&1; then
  sudo ufw status || true
else
  echo "ufw non installato."
fi

section "Prove"
echo "Dentro la VM:"
echo "  curl -I http://127.0.0.1:${PORT}"
echo "Dal PC host/LAN:"
echo "  http://IP_DELLA_VM:${PORT}"
echo
echo "Se il servizio e active ma il browser non risponde, controlla IP cambiato, scheda VirtualBox bridge/NAT e firewall."
