# Console GG Public Release Design

## Goal

Prepare Console GG for a public Git repository and more reliable VM use by making deployment easier to understand, adding a lightweight access gate for the browser arcade, improving the browser UI, and cleaning generated artifacts.

## Scope

- Keep the existing Python game architecture.
- Reorganize deployment documentation around two clear targets: Linux and Windows.
- Keep Linux Docker and Linux native systemd paths available.
- Keep Windows Home support using a resilient startup Scheduled Task, documented as the Windows service strategy.
- Add browser login with an allowed-username whitelist and optional shared access code.
- Add optional ttyd Basic Auth for native Linux.
- Improve the web terminal page visually without changing the game runtime.
- Update Block Dropper initial gravity to `0.70`.
- Remove generated `__pycache__` folders and improve ignore rules.

## Architecture

The browser arcade remains a small Node.js service in `deploy/web-terminal`. It serves static assets and spawns the installed Console GG command inside a PTY. Access control happens before WebSocket session creation: unauthenticated requests see a login screen, accepted users receive a signed cookie, and WebSocket upgrades are rejected unless the cookie is valid.

Deployment docs and scripts are organized by platform. Windows remains in `deploy/windows`. Linux scripts move into `deploy/linux`, while compatibility wrapper scripts stay at the old paths so existing commands continue to work. Docker remains at the repository root because `docker compose` expects root context.

## Access Model

The whitelist accepts usernames from `CONSOLE_GG_ALLOWED_USERS`, comma-separated. If the variable is missing, the browser arcade allows local/LAN use without login to preserve current behavior for quick installs. If `CONSOLE_GG_ACCESS_CODE` is set, login requires both allowed username and access code. Cookie signing uses `CONSOLE_GG_SESSION_SECRET`; if not set, the access code is reused as the secret, then a local development fallback is used.

This is intentionally a lightweight LAN gate, not internet-grade identity. Public exposure should still use VPN, firewall, or a reverse proxy.

## Visual Direction

The web page should feel like a compact modern arcade console: darker neutral base, clear terminal focus, restrained neon accents, better status states, and mobile-safe spacing. The first screen is the usable terminal/login experience, not a marketing landing page.

## Testing

Use Python `unittest` contract tests for deploy scripts/docs and static web assets. Use `node --check` for server/client syntax. Use `python -m compileall -q -x "node_modules|\.git|\.venv" .` for Python syntax.
