#!/usr/bin/env bash
set -u

PORT="${PORT:-7681}"

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

section() {
  echo
  echo "=== $1 ==="
}

section "Docker"
systemctl is-active docker || true
docker --version || true
docker compose version || true

section "Compose"
docker compose ps || true

section "Container log"
docker logs console-gg --tail 100 || true

section "Porta ${PORT}"
ss -ltnp "sport = :${PORT}" || sudo ss -ltnp "sport = :${PORT}" || true

section "IP della VM"
hostname -I || true

section "Comandi utili"
echo "Avvia/aggiorna: bash start-linux.sh"
echo "Ferma:         bash stop-linux.sh"
echo "Log live:      docker logs -f console-gg"
