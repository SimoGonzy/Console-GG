[CmdletBinding()]
param(
    [string]$AppDir = $(if ($env:CONSOLE_GG_APP_DIR) { $env:CONSOLE_GG_APP_DIR } else { "C:\ConsoleGG" }),
    [string]$StateDir = $(if ($env:CONSOLE_GG_STATE_DIR) { $env:CONSOLE_GG_STATE_DIR } else { "$env:ProgramData\ConsoleGG" })
)

$ErrorActionPreference = "Stop"

function Resolve-StateDir {
    param([string]$RequestedPath)

    $candidatePaths = New-Object System.Collections.Generic.List[string]
    $candidatePaths.Add($RequestedPath)
    $candidatePaths.Add((Join-Path $AppDir ".console-gg-data"))
    if ($env:LOCALAPPDATA) {
        $candidatePaths.Add((Join-Path $env:LOCALAPPDATA "ConsoleGG"))
    }
    if ($env:TEMP) {
        $candidatePaths.Add((Join-Path $env:TEMP "ConsoleGG"))
    }

    $seen = @{}
    foreach ($candidatePath in $candidatePaths) {
        if (-not $candidatePath -or $seen.ContainsKey($candidatePath)) {
            continue
        }
        $seen[$candidatePath] = $true
        try {
            New-Item -ItemType Directory -Force -Path $candidatePath -ErrorAction Stop | Out-Null
            return (Resolve-Path -LiteralPath $candidatePath).Path
        } catch [System.UnauthorizedAccessException] {
            continue
        } catch {
            if ($_.Exception -is [System.UnauthorizedAccessException]) {
                continue
            }
            throw
        }
    }

    throw "Nessuna directory statistiche scrivibile trovata. Controlla StateDir, AppDir, LOCALAPPDATA o TEMP."
}

$resolvedStateDir = Resolve-StateDir -RequestedPath $StateDir

$env:CONSOLE_GG_STATS_PATH = Join-Path $resolvedStateDir "console_gg_stats.json"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONDONTWRITEBYTECODE = "1"

$consoleGg = Join-Path $AppDir ".venv\Scripts\console-gg.exe"
if (Test-Path $consoleGg) {
    & $consoleGg
    exit $LASTEXITCODE
}

$sourceMain = Join-Path $AppDir "main.py"
if (Test-Path $sourceMain) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & $py.Source -3 $sourceMain
        exit $LASTEXITCODE
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source $sourceMain
        exit $LASTEXITCODE
    }

    throw "Python non trovato. Installa Python 3.11+ o esegui deploy\windows\install-windows-ssh.ps1."
}

throw "console-gg non trovato in $consoleGg e main.py non trovato in $sourceMain. Esegui prima deploy\windows\install-windows-ssh.ps1"
