[CmdletBinding()]
param(
    [int]$Port = 7681,
    [int]$SshPort = 22
)

$ErrorActionPreference = "Stop"

function Get-ConsoleGgIpv4Addresses {
    return Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*"
        } |
        Sort-Object InterfaceAlias, IPAddress
}

function Assert-LocalSshReady {
    $sshd = Get-Service -Name sshd -ErrorAction SilentlyContinue
    if (-not $sshd) {
        throw "Wetty usa SSH locale, ma il servizio 'sshd' non esiste. Esegui prima deploy\windows\install-windows-ssh.ps1."
    }

    if ($sshd.Status -ne "Running") {
        Start-Service -Name sshd
        $sshd = Get-Service -Name sshd -ErrorAction SilentlyContinue
    }

    $sshReady = Test-NetConnection -ComputerName 127.0.0.1 -Port $SshPort -InformationLevel Quiet
    if (-not $sshReady) {
        throw "Wetty usa SSH locale, ma 127.0.0.1:$SshPort non risponde. Esegui deploy\windows\diagnose-network.ps1."
    }
}

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    throw "npx non trovato. Installa Node.js LTS per usare Wetty."
}

Assert-LocalSshReady

if (-not (Get-NetFirewallRule -Name "ConsoleGG-Wetty" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule `
        -Name "ConsoleGG-Wetty" `
        -DisplayName "Console GG Wetty" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $Port `
        -Action Allow
}

Write-Host ""
Write-Host "Wetty pronto sulla porta $Port."
Write-Host "Lascia questa finestra aperta: chiudendola si ferma il terminale web."
Write-Host "IMPORTANTE: Wetty qui usa HTTP semplice. NON usare https:// su questa porta."
Write-Host "URL possibili dalla rete:"
foreach ($address in Get-ConsoleGgIpv4Addresses) {
    Write-Host "  http://$($address.IPAddress):$Port"
}
Write-Host ""

npx wetty --host 0.0.0.0 --port $Port --ssh-host 127.0.0.1 --ssh-port $SshPort
