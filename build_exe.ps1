$ErrorActionPreference = "Stop"

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found. Run: python -m venv .venv"
}

& $python -m PyInstaller --noconfirm --windowed --name "Local PDF Converter" run_app.py

