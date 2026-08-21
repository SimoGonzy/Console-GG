# Windows Arcade Kiosk Design

## Goal

Console GG on a Windows 10 Home VM should feel like an always-on arcade cabinet:
open a browser URL or run one SSH command, and the game menu appears without
typing a second command.

## Browser Mode

The browser path is LAN-only and intentionally has no login. A local Node.js
service listens on `0.0.0.0:7681`, serves a small xterm.js page, and creates a
fresh pseudo-terminal session for each browser connection. The child process is:

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File C:\ConsoleGG\deploy\windows\run-console-gg.ps1
```

Closing the browser closes that game session. Opening the URL again starts a new
session.

## SSH Mode

SSH remains password/key based because Windows/OpenSSH should not allow remote
login for an account with an empty password. The installer can create/use a
dedicated `arcade` local user and append a `Match User arcade` block to
`C:\ProgramData\ssh\sshd_config` with a `ForceCommand` that launches Console GG.
That makes `ssh arcade@VM_IP` enter the game directly.

## Startup

The browser service is registered as a Windows Scheduled Task running as
`SYSTEM` at startup. It uses the absolute Node.js path discovered during install,
so it does not depend on a user-specific `PATH`.

## Safety

The browser service is unauthenticated by design and must stay on trusted LAN or
behind VM/firewall rules. The docs should make this explicit and keep the old
Wetty flow as legacy/optional rather than the recommended browser path.
