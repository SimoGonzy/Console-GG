# Windows Arcade Kiosk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an always-on Windows arcade mode where browser and SSH access launch Console GG directly.

**Architecture:** Add a small Node.js xterm.js/node-pty web terminal for no-login LAN browser play. Add Windows PowerShell scripts that install dependencies, register a startup scheduled task, and optionally configure an SSH `ForceCommand` for a dedicated arcade user.

**Tech Stack:** Python 3.11+, PowerShell 5.1+, Node.js LTS, xterm.js, node-pty, ws.

## Global Constraints

- Browser mode listens on port `7681` and is LAN-only/no-login by design.
- SSH still requires password or key authentication.
- Windows scripts must be parseable by PowerShell before shipping.
- Existing game code should not be refactored for this deploy task.

---

### Task 1: Tests

**Files:**
- Modify: `tests/test_windows_deploy.py`

**Interfaces:**
- Consumes: deploy files as plain text.
- Produces: regression checks for arcade deploy files and docs.

- [ ] Add failing tests for `deploy/web-terminal/server.js`, `deploy/windows/start-arcade-web.ps1`, and `deploy/windows/install-windows-arcade.ps1`.
- [ ] Run `python -m unittest tests.test_windows_deploy` and verify the new tests fail before implementation.

### Task 2: Browser Arcade Server

**Files:**
- Create: `deploy/web-terminal/package.json`
- Create: `deploy/web-terminal/server.js`
- Create: `deploy/web-terminal/public/index.html`
- Create: `deploy/web-terminal/public/client.js`
- Create: `deploy/web-terminal/public/style.css`

**Interfaces:**
- Consumes: `CONSOLE_GG_APP_DIR`, `CONSOLE_GG_STATE_DIR`, `CONSOLE_GG_PORT`, `CONSOLE_GG_HOST`.
- Produces: HTTP server and WebSocket PTY endpoint at `/ws`.

- [ ] Implement a Node.js server that serves static assets and spawns `run-console-gg.ps1` with node-pty for each websocket.
- [ ] Implement xterm.js browser UI that connects to `/ws`, forwards keyboard input, and resizes the PTY.
- [ ] Run tests.

### Task 3: Windows Startup Scripts

**Files:**
- Create: `deploy/windows/start-arcade-web.ps1`
- Create: `deploy/windows/install-windows-arcade.ps1`
- Modify: `deploy/windows/install-windows-ssh.ps1`

**Interfaces:**
- Consumes: existing `install-windows-ssh.ps1` and `run-console-gg.ps1`.
- Produces: scheduled task `ConsoleGG Arcade Web` and optional SSH forced command.

- [ ] Implement `start-arcade-web.ps1` to validate Node, firewall, app paths, and launch the web terminal server.
- [ ] Implement `install-windows-arcade.ps1` to run base install, install npm dependencies, configure SSH kiosk user, and register/start the scheduled task.
- [ ] Run PowerShell parser checks.

### Task 4: Documentation

**Files:**
- Modify: `deploy/windows/README.md`
- Modify: `deploy/README.md`

**Interfaces:**
- Consumes: final script names and commands.
- Produces: copy/paste VM install flow.

- [ ] Document recommended arcade mode first.
- [ ] Keep Wetty as legacy optional.
- [ ] Run tests and parser checks.
