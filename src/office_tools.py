"""LibreOffice-based document conversion, run locally in headless mode."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .output_paths import safe_output_path


COMMON_WINDOWS_SOFFICE_PATHS = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
]

# Import filter that makes LibreOffice open a PDF in Writer instead of Draw, which keeps
# text flowing as paragraphs rather than as one text box per line.
PDF_WRITER_IMPORT = "writer_pdf_import"

PDFA_VERSIONS = {"PDF/A-1b": 1, "PDF/A-2b": 2, "PDF/A-3b": 3}


def find_libreoffice() -> Path | None:
    path_value = shutil.which("soffice") or shutil.which("soffice.exe")
    if path_value:
        return Path(path_value)

    for candidate in COMMON_WINDOWS_SOFFICE_PATHS:
        if candidate.exists():
            return candidate
    return None


def convert_with_libreoffice(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    target: str,
    output_suffix: str | None = None,
    output_stem: str | None = None,
    infilter: str | None = None,
    soffice_path: str | Path | None = None,
    timeout_seconds: int = 180,
) -> Path:
    """Convert one file with LibreOffice and move the result into output_dir.

    `target` is a LibreOffice --convert-to value, for example "pdf", "docx", or
    'pdf:draw_pdf_Export:{"SelectPdfVersion":{"type":"long","value":1}}'.
    """
    source = Path(input_path).resolve()
    soffice = Path(soffice_path) if soffice_path else find_libreoffice()
    if not soffice:
        raise RuntimeError("LibreOffice was not found. Install it to enable this conversion.")

    suffix = output_suffix or f".{target.split(':')[0]}"
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".lo_convert_", dir=output_root) as temp_dir:
        command = [str(soffice), "--headless"]
        if infilter:
            command.append(f"--infilter={infilter}")
        command += ["--convert-to", target, "--outdir", temp_dir, str(source)]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"LibreOffice took longer than {timeout_seconds} seconds on {source.name}."
            ) from exc

        generated = Path(temp_dir) / f"{source.stem}{suffix}"
        if completed.returncode != 0 or not generated.exists():
            details = (completed.stderr or completed.stdout or "LibreOffice created no output.").strip()
            raise RuntimeError(f"LibreOffice conversion failed for {source.name}: {details}")

        output_path = safe_output_path(output_root, output_stem or source.stem, suffix)
        shutil.move(str(generated), str(output_path))
        return output_path


def convert_office_to_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    soffice_path: str | Path | None = None,
    timeout_seconds: int = 120,
) -> Path:
    """Convert a Word, PowerPoint or Excel file to PDF."""
    return convert_with_libreoffice(
        input_path,
        output_dir,
        target="pdf",
        soffice_path=soffice_path,
        timeout_seconds=timeout_seconds,
    )


def pdf_to_word(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    soffice_path: str | Path | None = None,
) -> Path:
    """Best-effort PDF to DOCX using the LibreOffice Writer PDF import filter."""
    return convert_with_libreoffice(
        input_path,
        output_dir,
        target="docx",
        infilter=PDF_WRITER_IMPORT,
        soffice_path=soffice_path,
    )


def pdf_to_pdfa(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    version: str = "PDF/A-2b",
    soffice_path: str | Path | None = None,
) -> Path:
    """Convert a PDF to an archival PDF/A file."""
    from .choices import match_choice

    label = match_choice(version, PDFA_VERSIONS, "a PDF/A version")
    options = {"SelectPdfVersion": {"type": "long", "value": PDFA_VERSIONS[label]}}
    target = f"pdf:draw_pdf_Export:{json.dumps(options, separators=(',', ':'))}"
    source = Path(input_path)
    return convert_with_libreoffice(
        source,
        output_dir,
        target=target,
        output_suffix=".pdf",
        output_stem=f"{source.stem}_pdfa",
        soffice_path=soffice_path,
    )
