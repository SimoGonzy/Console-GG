# Console GG Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Console GG cleaner to publish and more reliable to run on Linux/Windows VMs.

**Architecture:** Keep Python gameplay unchanged except Block Dropper gravity. Add access control in the Node browser terminal, platform-specific deploy folders, compatibility wrappers, and refreshed static UI.

**Tech Stack:** Python 3.11+, unittest, PowerShell, Bash, systemd, Docker Compose, Node.js, ws, node-pty, xterm.

## Global Constraints

- Preserve existing launcher commands where possible.
- Do not remove user-authored source files.
- Treat browser login as a LAN safety gate, not a replacement for network security.
- Do not require new runtime dependencies for Python.
- Keep web UI code-native and immediately usable.

---

### Task 1: Access Gate Tests

**Files:**
- Modify: `tests/test_windows_deploy.py`

**Interfaces:**
- Produces expectations for `CONSOLE_GG_ALLOWED_USERS`, `CONSOLE_GG_ACCESS_CODE`, signed cookies, login form, and WebSocket auth checks.

- [ ] Add failing tests that assert the web terminal has login and whitelist support.
- [ ] Run `python -m unittest tests.test_windows_deploy -v` and confirm the new tests fail.
- [ ] Implement access gate in `deploy/web-terminal/server.js`, `public/index.html`, `public/client.js`, and `public/style.css`.
- [ ] Re-run `python -m unittest tests.test_windows_deploy -v`.

### Task 2: Platform Deploy Layout

**Files:**
- Create: `deploy/linux/README.md`
- Move/add wrappers for Linux scripts while preserving old commands.
- Modify: `deploy/README.md`, `README.md`, deploy tests.

**Interfaces:**
- Produces `deploy/linux` and `deploy/windows` as the two documented platform cards.

- [ ] Add failing tests that assert `deploy/linux/README.md` exists and old root deploy scripts are compatibility wrappers.
- [ ] Run deploy tests and confirm failures.
- [ ] Move Linux implementation scripts into `deploy/linux`.
- [ ] Add root wrapper scripts for old command compatibility.
- [ ] Update README files.
- [ ] Re-run deploy tests.

### Task 3: Linux Auth and Windows Service Clarity

**Files:**
- Modify: Linux systemd/Docker docs and Windows installer docs/scripts.

**Interfaces:**
- Produces optional `CONSOLE_GG_TTYD_CREDENTIAL` for native Linux and documented Windows startup-task service behavior.

- [ ] Add failing tests for optional ttyd credential environment and Windows service wording.
- [ ] Update systemd service, Linux installer docs, and Windows README.
- [ ] Re-run deploy tests.

### Task 4: Block Dropper Gravity

**Files:**
- Create or modify: `tests/test_block_dropper.py`
- Modify: `console_gg/games/block_dropper.py`

**Interfaces:**
- Produces `gravity_period(1) == 0.70`.

- [ ] Add failing test for initial gravity period.
- [ ] Run the specific test and confirm failure.
- [ ] Change `INITIAL_GRAVITY_PERIOD` to `0.70`.
- [ ] Re-run the test.

### Task 5: Repository Hygiene and Verification

**Files:**
- Modify: `.gitignore`
- Remove: generated `__pycache__` folders.

**Interfaces:**
- Produces a clean repo surface and corrected test command.

- [ ] Improve `.gitignore` for common Python/Node/local artifacts.
- [ ] Remove generated cache directories.
- [ ] Run `python -m unittest discover -s tests -p "test*.py" -v`.
- [ ] Run `python -m compileall -q -x "node_modules|\.git|\.venv" .`.
- [ ] Run `node --check deploy/web-terminal/server.js` and `node --check deploy/web-terminal/public/client.js`.
