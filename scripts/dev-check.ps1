[CmdletBinding()]
param(
    [switch]$Frontend
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$environmentFile = Join-Path $projectRoot ".env"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw "Missing $environmentFile. Copy .env.example to .env and set the local PostgreSQL values."
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing $python. Create the project virtual environment before running this check."
}

Push-Location $projectRoot
try {
    & $python backend/manage.py check
    & $python backend/manage.py makemigrations --check --dry-run

    if ($Frontend) {
        $npm = Get-Command npm.cmd -ErrorAction Stop
        Push-Location (Join-Path $projectRoot "frontend")
        try {
            & $npm.Source run lint
        }
        finally {
            Pop-Location
        }
    }
}
finally {
    Pop-Location
}
