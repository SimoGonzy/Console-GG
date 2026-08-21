[CmdletBinding()]
param(
    [int]$SshPort = 22,
    [Alias("WettyPort")]
    [int]$WebPort = 7681,
    [string]$UserName = $env:USERNAME
)

$ErrorActionPreference = "Continue"

function Write-Section {
    param([string]$Title)

    Write-Host ""
    Write-Host "=== $Title ==="
}

function Get-ConsoleGgIpv4Addresses {
    return Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*"
        } |
        Sort-Object InterfaceAlias, IPAddress
}

function Write-FirewallRule {
    param([string]$Name)

    $rule = Get-NetFirewallRule -Name $Name -ErrorAction SilentlyContinue
    if (-not $rule) {
        Write-Host "${Name}: mancante"
        return
    }

    Write-Host "${Name}: Enabled=$($rule.Enabled) Profile=$($rule.Profile) Action=$($rule.Action)"
}

Write-Section "Sistema"
Write-Host "Computer: $env:COMPUTERNAME"
Write-Host "Utente: $UserName"
Write-Host "PowerShell: $($PSVersionTable.PSVersion)"

Write-Section "Servizi"
$sshd = Get-Service -Name sshd -ErrorAction SilentlyContinue
if (-not $sshd) {
    Write-Host "sshd: MANCANTE"
} else {
    $sshdConfig = Get-CimInstance Win32_Service -Filter "Name='sshd'" -ErrorAction SilentlyContinue
    Write-Host "sshd: Status=$($sshd.Status) StartMode=$($sshdConfig.StartMode)"
}

Write-Section "Task Arcade"
$arcadeTask = Get-ScheduledTask -TaskName "ConsoleGG Arcade Web" -ErrorAction SilentlyContinue
if (-not $arcadeTask) {
    Write-Host "ConsoleGG Arcade Web: MANCANTE"
} else {
    Write-Host "ConsoleGG Arcade Web: State=$($arcadeTask.State)"
}

Write-Section "Porte locali"
$sshListeners = @(Get-NetTCPConnection -LocalPort $SshPort -State Listen -ErrorAction SilentlyContinue)
$webListeners = @(Get-NetTCPConnection -LocalPort $WebPort -State Listen -ErrorAction SilentlyContinue)

Write-Host "Listener SSH ${SshPort}: $($sshListeners.Count)"
foreach ($listener in $sshListeners) {
    Write-Host "  $($listener.LocalAddress):$($listener.LocalPort) pid=$($listener.OwningProcess)"
}

Write-Host "Listener Web ${WebPort}: $($webListeners.Count)"
foreach ($listener in $webListeners) {
    Write-Host "  $($listener.LocalAddress):$($listener.LocalPort) pid=$($listener.OwningProcess)"
}

$sshLocalOk = Test-NetConnection -ComputerName 127.0.0.1 -Port $SshPort -InformationLevel Quiet
$webLocalOk = Test-NetConnection -ComputerName 127.0.0.1 -Port $WebPort -InformationLevel Quiet
Write-Host "Test locale SSH 127.0.0.1:${SshPort}: $sshLocalOk"
Write-Host "Test locale Web 127.0.0.1:${WebPort}: $webLocalOk"

Write-Section "Firewall"
Write-FirewallRule -Name "ConsoleGG-SSH"
Write-FirewallRule -Name "ConsoleGG-Arcade-Web"
Write-FirewallRule -Name "ConsoleGG-Wetty"

Write-Section "IP della VM"
$addresses = @(Get-ConsoleGgIpv4Addresses)
if ($addresses.Count -eq 0) {
    Write-Host "Nessun IPv4 utile trovato."
} else {
    foreach ($address in $addresses) {
        Write-Host "$($address.InterfaceAlias): $($address.IPAddress)"
    }
}

Write-Section "Prove dal PC host o da un PC della LAN"
foreach ($address in $addresses) {
    Write-Host "SSH:  ssh $UserName@$($address.IPAddress)"
    Write-Host "Web:  http://$($address.IPAddress):${WebPort}"
}
Write-Host "Se la VM usa NAT o port forwarding, l'IP della VM potrebbe non essere raggiungibile direttamente dalla LAN."
Write-Host "Esempio port forwarding: host 2222 -> guest $SshPort, host $WebPort -> guest $WebPort."
Write-Host "Poi dal PC host: ssh -p 2222 $UserName@127.0.0.1 oppure http://127.0.0.1:${WebPort}"

Write-Section "Interpretazione"
if (-not $sshLocalOk) {
    Write-Host "- SSH non funziona nemmeno dentro la VM: controlla installazione OpenSSH e servizio sshd."
} else {
    Write-Host "- SSH locale OK. Se da fuori non entra, il problema e rete VM/firewall esterno."
}

if (-not $webLocalOk) {
    Write-Host "- Web arcade non e in ascolto: avvia il task ConsoleGG Arcade Web o deploy\windows\start-arcade-web.ps1."
} else {
    Write-Host "- Web locale OK. Se il browser da fuori non apre, il problema e rete VM/NAT o HTTPS forzato dal browser."
}
