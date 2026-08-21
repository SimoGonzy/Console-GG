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

function Get-ToolPath {
    param([string[]]$Names)

    foreach ($name in $Names) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    throw "Tool non trovato: $($Names -join ', ')"
}

function Get-ConsoleGgIpv4Addresses {
    return Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*"
        } |
        Sort-Object InterfaceAlias, IPAddress
}

function Install-BaseConsoleGg {
    $baseInstaller = Join-Path $PSScriptRoot "install-windows-ssh.ps1"
    $arguments = @(
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $baseInstaller,
        "-AppDir", $AppDir,
        "-StateDir", $StateDir
    )

    if ($SkipOpenSSH) {
        $arguments += "-SkipOpenSSH"
    }

    & powershell.exe @arguments
}

function Install-WebDependencies {
    $webDir = Join-Path $AppDir "deploy\web-terminal"
    $packageFile = Join-Path $webDir "package.json"
    if (-not (Test-Path $packageFile)) {
        throw "package.json del cabinato web non trovato in $packageFile"
    }

    $npmPath = Get-ToolPath -Names @("npm.cmd", "npm")
    Push-Location $webDir
    try {
        & $npmPath install --omit=dev --no-audit
    } finally {
        Pop-Location
    }
}

function Ensure-ArcadeUser {
    if ($SkipArcadeUser) {
        return
    }

    $existingUser = Get-LocalUser -Name $ArcadeUser -ErrorAction SilentlyContinue
    if (-not $existingUser) {
        Write-Host ""
        Write-Host "Creo l'utente SSH arcade '$ArcadeUser'. Scegli una password: servira per ssh $ArcadeUser@IP_VM."
        $password = Read-Host -AsSecureString "Password per $ArcadeUser"
        New-LocalUser `
            -Name $ArcadeUser `
            -Password $password `
            -Description "Console GG arcade SSH user" `
            -PasswordNeverExpires | Out-Null
    }

    try {
        Add-LocalGroupMember -Group "Users" -Member $ArcadeUser -ErrorAction Stop
    } catch {
        Write-Verbose "Utente $ArcadeUser gia nel gruppo Users o gruppo non modificabile: $($_.Exception.Message)"
    }
}

function Set-ArcadeSshForceCommand {
    if ($SkipOpenSSH -or $SkipArcadeUser) {
        return
    }

    $configPath = Join-Path $env:ProgramData "ssh\sshd_config"
    if (-not (Test-Path $configPath)) {
        Write-Warning "sshd_config non trovato in $configPath. Salto configurazione ForceCommand."
        return
    }

    $runScript = Join-Path $AppDir "deploy\windows\run-console-gg.ps1"
    $forceCommand = "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$runScript`""
    $startMarker = "# BEGIN ConsoleGG Arcade"
    $endMarker = "# END ConsoleGG Arcade"
    $block = @(
        "",
        $startMarker,
        "Match User $ArcadeUser",
        "    ForceCommand $forceCommand",
        $endMarker
    ) -join [Environment]::NewLine

    $content = Get-Content -Path $configPath -Raw
    $pattern = "(?s)\r?\n?# BEGIN ConsoleGG Arcade.*?# END ConsoleGG Arcade\r?\n?"
    $cleanContent = [regex]::Replace($content, $pattern, "")
    Set-Content -Path $configPath -Value ($cleanContent.TrimEnd() + $block + [Environment]::NewLine) -Encoding ascii

    $sshd = Get-Service -Name sshd -ErrorAction SilentlyContinue
    if ($sshd) {
        Restart-Service -Name sshd
    }
}

function Register-ArcadeWebTask {
    if ($SkipWebTask) {
        return
    }

    $nodePath = Get-ToolPath -Names @("node.exe", "node")
    $startScript = Join-Path $AppDir "deploy\windows\start-arcade-web.ps1"
    if (-not (Test-Path $startScript)) {
        throw "Script web arcade non trovato in $startScript"
    }

    $taskName = "ConsoleGG Arcade Web"
    $argument = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$startScript`" -AppDir `"$AppDir`" -StateDir `"$StateDir`" -Port $WebPort -NodePath `"$nodePath`""
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
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Description "Console GG browser arcade terminal" `
        -Force | Out-Null

    Start-ScheduledTask -TaskName $taskName
}

Install-BaseConsoleGg
Install-WebDependencies
Ensure-ArcadeUser
Set-ArcadeSshForceCommand
Register-ArcadeWebTask

Write-Host ""
Write-Host "Console GG Arcade installato."
if ($AllowedUsers -or $AccessCode) {
    Write-Host "Browser con login/whitelist:"
    if ($AllowedUsers) {
        Write-Host "  CONSOLE_GG_ALLOWED_USERS=$AllowedUsers"
    }
} else {
    Write-Host "Browser senza login. Imposta -AllowedUsers e -AccessCode per attivare la whitelist."
}
foreach ($address in Get-ConsoleGgIpv4Addresses) {
    Write-Host "  http://$($address.IPAddress):${WebPort}"
}

if (-not $SkipArcadeUser) {
    Write-Host "SSH diretto al gioco:"
    foreach ($address in Get-ConsoleGgIpv4Addresses) {
        Write-Host "  ssh $ArcadeUser@$($address.IPAddress)"
    }
}

Write-Host ""
Write-Host "Task Windows: ConsoleGG Arcade Web"
Write-Host "Per diagnostica: powershell -ExecutionPolicy Bypass -File $AppDir\deploy\windows\diagnose-network.ps1"
