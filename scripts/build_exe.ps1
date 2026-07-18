$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$entryPoint = Join-Path $projectRoot "run_app.py"

if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found. From the project folder, run: python -m venv .venv"
}

Push-Location $projectRoot
try {
    & $python -m PyInstaller --noconfirm --windowed --name "Local PDF Converter" $entryPoint
}
finally {
    Pop-Location
}
