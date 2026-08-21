#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-docker}"

case "$MODE" in
  docker|--docker)
    bash "$ROOT_DIR/deploy/linux/docker-down.sh"
    ;;
  native|--native|systemd|--systemd)
    sudo systemctl stop console-gg-ttyd.service
    ;;
  -h|--help|help)
    cat <<'EOF'
Usage:
  bash stop-linux.sh          Stop the Docker web service.
  bash stop-linux.sh native   Stop the native systemd service.
EOF
    ;;
  *)
    echo "Modalita non valida: $MODE" >&2
    echo "Usa: docker oppure native" >&2
    exit 2
    ;;
esac
