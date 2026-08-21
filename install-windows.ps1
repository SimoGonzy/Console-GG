[CmdletBinding()]
param(
    [string]$AppDir = "C:\ConsoleGG",
    [string]$StateDir = "$env:ProgramData\ConsoleGG",
    [int]$WebPort = 7681,
    [string]$ArcadeUser = "arcade",
    [string]$AllowedUsers = "",
    [string]$AccessCode = "",
    [string]$SessionSecret = "",
    [switch]$SkipOpenSSH,
    [switch]$SkipArcadeUser,
    [switch]$SkipWebTask
)

$ErrorActionPreference = "Stop"

$installer = Join-Path $PSScriptRoot "deploy\windows\install-windows-arcade.ps1"
if (-not (Test-Path $installer)) {
    throw "Installer Windows non trovato: $installer"
}

$arguments = @{
    AppDir = $AppDir
    StateDir = $StateDir
    WebPort = $WebPort
    ArcadeUser = $ArcadeUser
}

if ($AllowedUsers) {
    $arguments.AllowedUsers = $AllowedUsers
}
if ($AccessCode) {
    $arguments.AccessCode = $AccessCode
}
if ($SessionSecret) {
    $arguments.SessionSecret = $SessionSecret
}
if ($SkipOpenSSH) {
    $arguments.SkipOpenSSH = $true
}
if ($SkipArcadeUser) {
    $arguments.SkipArcadeUser = $true
}
if ($SkipWebTask) {
    $arguments.SkipWebTask = $true
}

& $installer @arguments
