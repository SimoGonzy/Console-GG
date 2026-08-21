#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-docker}"

case "$MODE" in
  docker|--docker)
    bash "$ROOT_DIR/deploy/linux/docker-up.sh"
    ;;
  native|--native|systemd|--systemd)
    sudo systemctl start console-gg-ttyd.service
    sudo systemctl status console-gg-ttyd.service --no-pager -l
    ;;
  -h|--help|help)
    cat <<'EOF'
Usage:
  bash start-linux.sh          Start/update the Docker web service.
  bash start-linux.sh native   Start the native systemd service.
EOF
    ;;
  *)
    echo "Modalita non valida: $MODE" >&2
    echo "Usa: docker oppure native" >&2
    exit 2
    ;;
esac
