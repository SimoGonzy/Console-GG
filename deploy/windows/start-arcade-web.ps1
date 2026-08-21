[CmdletBinding()]
param(
    [string]$AppDir = "C:\ConsoleGG",
    [string]$StateDir = "$env:ProgramData\ConsoleGG",
    [int]$Port = 7681,
    [string]$HostName = "0.0.0.0",
    [string]$NodePath = "",
    [string]$AllowedUsers = "",
    [string]$AccessCode = "",
    [string]$SessionSecret = ""
)

$ErrorActionPreference = "Stop"

function Resolve-NodeExecutable {
    if ($NodePath) {
        $resolved = Resolve-Path -LiteralPath $NodePath -ErrorAction SilentlyContinue
        if ($resolved) {
            return $resolved.Path
        }
        throw "Node.js non trovato in NodePath: $NodePath"
    }

    $node = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($node) {
        return $node.Source
    }

    $node = Get-Command node -ErrorAction SilentlyContinue
    if ($node) {
        return $node.Source
    }

    throw "node non trovato. Installa Node.js LTS e rilancia install-windows-arcade.ps1."
}

function Get-ConsoleGgIpv4Addresses {
    return Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*"
        } |
        Sort-Object InterfaceAlias, IPAddress
}

$webDir = Join-Path $AppDir "deploy\web-terminal"
$serverScript = Join-Path $webDir "server.js"
if (-not (Test-Path $serverScript)) {
    throw "Server arcade non trovato in $serverScript. Rilancia install-windows-arcade.ps1 dalla root aggiornata del progetto."
}

$nodeExecutable = Resolve-NodeExecutable
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

if (-not (Get-NetFirewallRule -Name "ConsoleGG-Arcade-Web" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule `
        -Name "ConsoleGG-Arcade-Web" `
        -DisplayName "Console GG Arcade Web" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $Port `
        -Action Allow
}

$env:CONSOLE_GG_APP_DIR = $AppDir
$env:CONSOLE_GG_STATE_DIR = $StateDir
$env:CONSOLE_GG_HOST = $HostName
$env:CONSOLE_GG_PORT = [string]$Port
if ($AllowedUsers) {
    $env:CONSOLE_GG_ALLOWED_USERS = $AllowedUsers
}
if ($AccessCode) {
    $env:CONSOLE_GG_ACCESS_CODE = $AccessCode
}
if ($SessionSecret) {
    $env:CONSOLE_GG_SESSION_SECRET = $SessionSecret
}

Write-Host ""
Write-Host "Console GG Arcade Web pronto."
Write-Host "Lascia questo processo attivo se lo stai avviando manualmente."
Write-Host "IMPORTANTE: usa HTTP semplice. NON usare https:// su questa porta."
Write-Host "URL possibili dalla rete:"
foreach ($address in Get-ConsoleGgIpv4Addresses) {
    Write-Host "  http://$($address.IPAddress):${Port}"
}
if ($AllowedUsers) {
    Write-Host "Whitelist browser: $AllowedUsers"
}
Write-Host ""

Push-Location $webDir
try {
    & $nodeExecutable $serverScript
} finally {
    Pop-Location
}
