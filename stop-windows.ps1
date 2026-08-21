[CmdletBinding()]
param(
    [string]$TaskName = "ConsoleGG Arcade Web"
)

$ErrorActionPreference = "Stop"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    throw "Task '$TaskName' non trovato. Niente da fermare."
}

Stop-ScheduledTask -TaskName $TaskName
Get-ScheduledTask -TaskName $TaskName
