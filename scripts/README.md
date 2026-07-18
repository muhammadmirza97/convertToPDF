# Developer Scripts

This folder contains project-maintenance and packaging utilities. Normal users do not need these scripts to run Local PDF Converter.

## Windows EXE Build

`build_exe.ps1` packages `run_app.py` with PyInstaller. From the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\scripts\build_exe.ps1
```

The script resolves the project root automatically, so it can also be invoked from another working directory.
