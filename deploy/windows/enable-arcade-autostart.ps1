[CmdletBinding()]
param(
    [string]$AppDir = "C:\ConsoleGG",
    [string]$StateDir = "$env:ProgramData\ConsoleGG",
    [int]$WebPort = 7681,
    [string]$TaskName = "ConsoleGG Arcade Web",
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

    throw "node non trovato. Installa Node.js LTS e rilancia questo script."
}

$startScript = Join-Path $AppDir "deploy\windows\start-arcade-web.ps1"
if (-not (Test-Path $startScript)) {
    throw "Script arcade web non trovato: $startScript"
}

$nodeExecutable = Resolve-NodeExecutable
$argument = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$startScript`" -AppDir `"$AppDir`" -StateDir `"$StateDir`" -Port $WebPort -NodePath `"$nodeExecutable`""
if ($AllowedUsers) {
    $argument += " -AllowedUsers `"$AllowedUsers`""
}
if ($AccessCode) {
    $argument += " -AccessCode `"$AccessCode`""
}
if ($SessionSecret) {
    $argument += " -SessionSecret `"$SessionSecret`""
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 3650) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Console GG browser arcade terminal" `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName

Write-Host ""
Write-Host "$TaskName si avvia automaticamente al boot."
if ($AllowedUsers -or $AccessCode) {
    Write-Host "Whitelist/login configurati tramite CONSOLE_GG_ALLOWED_USERS e CONSOLE_GG_ACCESS_CODE."
}
Write-Host "Task avviato ora. Controllo:"
Write-Host "  Get-ScheduledTask `"$TaskName`""
Write-Host "Browser:"
Write-Host "  http://IP_DELLA_VM:$WebPort"
