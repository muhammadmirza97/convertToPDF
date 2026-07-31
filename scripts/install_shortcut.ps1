# Creates the "Local PDF Toolbox" desktop icon.
#
#   .\scripts\install_shortcut.ps1              # Desktop only
#   .\scripts\install_shortcut.ps1 -StartMenu   # Desktop and Start menu
#   .\scripts\install_shortcut.ps1 -Remove      # delete the shortcuts again
#
# The shortcut runs pythonw.exe from the project virtual environment, so double-clicking it
# opens the app with no console window.

param(
    [switch]$StartMenu,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonw = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
$entryPoint = Join-Path $projectRoot "run_app.py"
$iconPath = Join-Path $projectRoot "assets\app_icon.ico"
$shortcutName = "Local PDF Toolbox.lnk"

$targets = @([System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), $shortcutName))
if ($StartMenu -or $Remove) {
    $programs = [Environment]::GetFolderPath("Programs")
    $targets += [System.IO.Path]::Combine($programs, $shortcutName)
}

if ($Remove) {
    foreach ($target in $targets) {
        if (Test-Path $target) {
            Remove-Item $target -Force
            Write-Host "Removed $target"
        }
    }
    return
}

if (-not (Test-Path $pythonw)) {
    Write-Error "Virtual environment not found at $pythonw. Create it first: python -m venv .venv"
}
if (-not (Test-Path $entryPoint)) {
    Write-Error "run_app.py not found in $projectRoot"
}

$shell = New-Object -ComObject WScript.Shell
foreach ($target in $targets) {
    $parent = Split-Path $target -Parent
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force $parent | Out-Null
    }

    $shortcut = $shell.CreateShortcut($target)
    $shortcut.TargetPath = $pythonw
    $shortcut.Arguments = "`"$entryPoint`""
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.Description = "Local PDF Toolbox - offline PDF tools"
    $shortcut.WindowStyle = 1
    if (Test-Path $iconPath) {
        $shortcut.IconLocation = "$iconPath,0"
    }
    $shortcut.Save()
    Write-Host "Created $target"
}

[System.Runtime.InteropServices.Marshal]::ReleaseComObject($shell) | Out-Null
Write-Host "Double-click the icon to start the app."
