"""LibreOffice-based Office document conversion."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .output_paths import safe_output_path


COMMON_WINDOWS_SOFFICE_PATHS = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
]


def find_libreoffice() -> Path | None:
    path_value = shutil.which("soffice") or shutil.which("soffice.exe")
    if path_value:
        return Path(path_value)

    for candidate in COMMON_WINDOWS_SOFFICE_PATHS:
        if candidate.exists():
            return candidate
    return None


def convert_office_to_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    soffice_path: str | Path | None = None,
    timeout_seconds: int = 120,
) -> Path:
    source = Path(input_path).resolve()
    soffice = Path(soffice_path) if soffice_path else find_libreoffice()
    if not soffice:
        raise RuntimeError("LibreOffice was not found. Install it to enable Office-to-PDF conversion.")

    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".lo_convert_", dir=output_root) as temp_dir:
        command = [
            str(soffice),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            temp_dir,
            str(source),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        generated = Path(temp_dir) / f"{source.stem}.pdf"
        if completed.returncode != 0 or not generated.exists():
            details = (completed.stderr or completed.stdout or "LibreOffice did not create a PDF.").strip()
            raise RuntimeError(f"LibreOffice conversion failed for {source.name}: {details}")

        output_path = safe_output_path(output_root, source.stem, ".pdf")
        shutil.move(str(generated), str(output_path))
        return output_path

