[CmdletBinding()]
param(
    [string]$TaskName = "ConsoleGG Arcade Web",
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"

if ($Foreground) {
    $startScript = Join-Path $PSScriptRoot "deploy\windows\start-arcade-web.ps1"
    if (-not (Test-Path $startScript)) {
        throw "Script web Windows non trovato: $startScript"
    }
    & $startScript
    exit
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    throw "Task '$TaskName' non trovato. Esegui prima .\install-windows.ps1 oppure usa .\start-windows.ps1 -Foreground."
}

Start-ScheduledTask -TaskName $TaskName
Get-ScheduledTask -TaskName $TaskName
