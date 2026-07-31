# Builds a windowed Windows executable with PyInstaller.
#
#   .\scripts\build_exe.ps1
#
# Packaging is optional. Day to day, use the desktop icon from install_shortcut.ps1.

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found at $python. Create it first: python -m venv .venv"
}

$icon = Join-Path $projectRoot "assets\app_icon.ico"
$iconArgs = if (Test-Path $icon) { @("--icon", $icon) } else { @() }

Push-Location $projectRoot
try {
    & $python -m PyInstaller --noconfirm --windowed --name "Local PDF Toolbox" `
        @iconArgs --add-data "assets;assets" run_app.py
}
finally {
    Pop-Location
}
