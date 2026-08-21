[CmdletBinding()]
param(
    [string]$AppDir = "C:\ConsoleGG",
    [string]$StateDir = "$env:ProgramData\ConsoleGG",
    [switch]$SkipOpenSSH,
    [string]$OpenSshMsiPath = ""
)

$ErrorActionPreference = "Stop"

function Get-PythonLauncher {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @($py.Source, "-3")
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }

    throw "Python non trovato. Installa Python 3.11+ e abilita 'Add python.exe to PATH'."
}

function Get-SshdService {
    return Get-Service -Name sshd -ErrorAction SilentlyContinue
}

function Install-OpenSshCapability {
    $capability = Get-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 -ErrorAction SilentlyContinue
    if (-not $capability) {
        Write-Warning "Capability OpenSSH.Server non trovata da Windows."
        return
    }

    if ($capability.State -ne "Installed") {
        try {
            Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 -ErrorAction Stop | Out-Null
        } catch {
            Write-Warning "Installazione OpenSSH.Server fallita: $($_.Exception.Message)"
        }
    }
}

function Install-OpenSshMsi {
    param([string]$Path)

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $resolved) {
        throw "OpenSSH MSI non trovato: $Path"
    }

    Write-Host "Installazione OpenSSH da MSI: $($resolved.Path)"
    $process = Start-Process `
        -FilePath msiexec.exe `
        -ArgumentList @("/i", $resolved.Path, "/quiet", "/norestart") `
        -Wait `
        -PassThru

    if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 3010) {
        throw "Installazione OpenSSH MSI fallita con exit code $($process.ExitCode)"
    }
}

function Throw-MissingSshdService {
    $capabilities = @(
        Get-WindowsCapability -Online -ErrorAction SilentlyContinue |
            Where-Object Name -like "OpenSSH.Server*" |
            ForEach-Object { "  - $($_.Name): $($_.State)" }
    )
    if ($capabilities.Count -eq 0) {
        $capabilityText = "  - nessuna capability OpenSSH.Server trovata"
    } else {
        $capabilityText = $capabilities -join [Environment]::NewLine
    }

    $message = @"
OpenSSH Server non risulta installato: il servizio 'sshd' non esiste.

Diagnostica rilevata:
$capabilityText

Puoi controllare manualmente con:
  Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'

Prossimi tentativi:
  1. Apri Impostazioni > App > Funzionalita facoltative e installa OpenSSH Server.
  2. Oppure rilancia questo script passando un installer MSI:
     .\deploy\windows\install-windows-ssh.ps1 -OpenSshMsiPath C:\Percorso\OpenSSH-Win64.msi
  3. Oppure usa -SkipOpenSSH per installare solo Console GG e configurare SSH a parte.
"@
    throw $message
}

if (-not $SkipOpenSSH) {
    if (-not (Get-SshdService)) {
        Install-OpenSshCapability
    }

    if (-not (Get-SshdService) -and $OpenSshMsiPath) {
        Install-OpenSshMsi -Path $OpenSshMsiPath
    }

    $sshd = Get-SshdService
    if (-not $sshd) {
        Throw-MissingSshdService
    }

    Set-Service -Name sshd -StartupType Automatic
    if ($sshd.Status -ne "Running") {
        Start-Service -Name sshd
    }

    if (-not (Get-NetFirewallRule -Name "ConsoleGG-SSH" -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule `
            -Name "ConsoleGG-SSH" `
            -DisplayName "Console GG SSH" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort 22 `
            -Action Allow
    }
}

$sourceDir = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

$robocopyArgs = @(
    $sourceDir,
    $AppDir,
    "/E",
    "/XD", ".git", ".agents", ".codex", ".superpowers", ".venv", "__pycache__", "node_modules", "winner_bot", "docs\superpowers",
    "/XF", "console_gg_stats.json", "*.pyc", "test_winner_bot_*.py"
)
& robocopy @robocopyArgs | Out-Host
if ($LASTEXITCODE -gt 7) {
    throw "Robocopy fallito con exit code $LASTEXITCODE"
}

$pythonLauncher = Get-PythonLauncher
if ($pythonLauncher.Length -gt 1) {
    & $pythonLauncher[0] $pythonLauncher[1] -m venv (Join-Path $AppDir ".venv")
} else {
    & $pythonLauncher[0] -m venv (Join-Path $AppDir ".venv")
}

$venvPython = Join-Path $AppDir ".venv\Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e $AppDir

Write-Host ""
Write-Host "Console GG installato in $AppDir"
Write-Host "Statistiche in $StateDir\console_gg_stats.json"
Write-Host "Diagnostica rete: powershell -ExecutionPolicy Bypass -File $AppDir\deploy\windows\diagnose-network.ps1"
Write-Host "Da un altro PC: ssh <utente-windows>@<IP_VM>"
Write-Host "Poi esegui: powershell -ExecutionPolicy Bypass -File $AppDir\deploy\windows\run-console-gg.ps1"
