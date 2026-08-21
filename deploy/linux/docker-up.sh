#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-7681}"

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker non trovato. Prima esegui: bash install-linux.sh" >&2
  exit 1
fi

if systemctl cat console-gg-ttyd.service >/dev/null 2>&1; then
  sudo systemctl disable --now console-gg-ttyd.service 2>/dev/null || true
  sudo systemctl reset-failed console-gg-ttyd.service 2>/dev/null || true
fi

if ss -ltnp "sport = :${PORT}" | grep -q ":${PORT}"; then
  echo "La porta ${PORT} risulta gia occupata:" >&2
  ss -ltnp "sport = :${PORT}" || true
  echo
  echo "Chiudi il processo indicato, poi rilancia: sudo bash start-linux.sh" >&2
  exit 1
fi

docker compose up -d --build
docker compose ps

echo
echo "Console GG Docker attivo su http://IP_DELLA_VM:${PORT}"
echo "Il container usa restart: unless-stopped e riparte con Docker al boot."
