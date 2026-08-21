#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-docker}"

case "$MODE" in
  docker|--docker)
    bash "$ROOT_DIR/deploy/linux/install-docker.sh"
    bash "$ROOT_DIR/deploy/linux/docker-up.sh"
    ;;
  native|--native|systemd|--systemd)
    bash "$ROOT_DIR/deploy/linux/install-linux.sh"
    ;;
  -h|--help|help)
    cat <<'EOF'
Usage:
  bash install-linux.sh          Install Docker and start Console GG on port 7681.
  bash install-linux.sh docker   Same as above.
  bash install-linux.sh native   Install the native systemd + ttyd service.

After install, open:
  http://IP_DELLA_VM:7681
EOF
    ;;
  *)
    echo "Modalita non valida: $MODE" >&2
    echo "Usa: docker oppure native" >&2
    exit 2
    ;;
esac
