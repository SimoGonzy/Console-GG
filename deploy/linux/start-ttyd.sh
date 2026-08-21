#!/usr/bin/env bash
set -euo pipefail

PORT="${CONSOLE_GG_PORT:-7681}"
CONSOLE_COMMAND="${CONSOLE_GG_COMMAND:-/opt/console-gg/.venv/bin/console-gg}"

args=(--writable --interface 0.0.0.0 --port "$PORT")
# Default listener shape: --interface 0.0.0.0 --port 7681.
if [ -n "${CONSOLE_GG_TTYD_CREDENTIAL:-}" ]; then
  args+=(--credential "$CONSOLE_GG_TTYD_CREDENTIAL")
fi

exec /usr/bin/ttyd "${args[@]}" "$CONSOLE_COMMAND"
