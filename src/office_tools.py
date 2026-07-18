"""LibreOffice-based Office document conversion."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz

from .config import PROJECT_ROOT
from .output_paths import safe_output_path


COMMON_WINDOWS_SOFFICE_PATHS = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
]


def _headless_launcher(soffice: Path) -> Path:
    """Use soffice.com on Windows so the caller waits for conversion completion."""
    console_launcher = soffice.with_name("soffice.com")
    return console_launcher if os.name == "nt" and console_launcher.exists() else soffice


def _libreoffice_profile_uri() -> str:
    """Return an isolated reusable profile so headless work never locks the user's profile."""
    profile = PROJECT_ROOT / "sample_files" / ".libreoffice_profile"
    profile.mkdir(parents=True, exist_ok=True)
    return profile.resolve().as_uri()


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
    launcher = _headless_launcher(soffice)

    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".lo_convert_", dir=output_root) as temp_dir:
        profile_uri = _libreoffice_profile_uri()
        command = [
            str(launcher),
            "--headless",
            f"-env:UserInstallation={profile_uri}",
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


def pdf_to_word(input_path: str | Path, output_dir: str | Path) -> Path:
    """Create an editable, text-first DOCX. Complex layout is approximate."""
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("python-docx is not installed.") from exc
    source = Path(input_path)
    output = safe_output_path(output_dir, source.stem, ".docx")
    target = Document()
    with fitz.open(source) as document:
        for number, page in enumerate(document):
            if number:
                target.add_page_break()
            for block in page.get_text("blocks", sort=True):
                text = str(block[4]).strip()
                if text:
                    target.add_paragraph(text)
    target.save(output)
    return output


def pdf_to_powerpoint(input_path: str | Path, output_dir: str | Path) -> Path:
    """Create one slide per PDF page with extracted text blocks."""
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
    except ImportError as exc:
        raise RuntimeError("python-pptx is not installed.") from exc
    source = Path(input_path)
    output = safe_output_path(output_dir, source.stem, ".pptx")
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(10), Inches(7.5)
    with fitz.open(source) as document:
        for page in document:
            slide = deck.slides.add_slide(deck.slide_layouts[6])
            for block in page.get_text("blocks", sort=True):
                x0, y0, x1, y1, text = block[:5]
                if not str(text).strip():
                    continue
                box = slide.shapes.add_textbox(
                    Inches(max(0, x0 / page.rect.width * 10)),
                    Inches(max(0, y0 / page.rect.height * 7.5)),
                    Inches(max(0.3, (x1 - x0) / page.rect.width * 10)),
                    Inches(max(0.2, (y1 - y0) / page.rect.height * 7.5)),
                )
                box.text_frame.text = str(text).strip()
                for paragraph in box.text_frame.paragraphs:
                    paragraph.font.size = Pt(10)
    deck.save(output)
    return output


def pdf_to_excel(input_path: str | Path, output_dir: str | Path) -> Path:
    """Extract detected tables into worksheets; fall back to page text rows."""
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("openpyxl is not installed.") from exc
    source = Path(input_path)
    output = safe_output_path(output_dir, source.stem, ".xlsx")
    workbook = Workbook()
    workbook.remove(workbook.active)
    with fitz.open(source) as document:
        for number, page in enumerate(document, start=1):
            sheet = workbook.create_sheet(f"Page {number}")
            tables = page.find_tables().tables
            if tables:
                row_number = 1
                for table in tables:
                    for row in table.extract():
                        for column, value in enumerate(row, start=1):
                            sheet.cell(row_number, column, value)
                        row_number += 1
                    row_number += 1
            else:
                for row_number, line in enumerate(page.get_text().splitlines(), start=1):
                    sheet.cell(row_number, 1, line)
    if not workbook.worksheets:
        workbook.create_sheet("Empty")
    workbook.save(output)
    return output


def convert_pdf_to_pdfa(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    soffice_path: str | Path | None = None,
    timeout_seconds: int = 120,
) -> Path:
    """Use LibreOffice's PDF/A-1 export filter when available."""
    source = Path(input_path).resolve()
    soffice = Path(soffice_path) if soffice_path else find_libreoffice()
    if not soffice:
        raise RuntimeError("LibreOffice was not found; PDF/A conversion is unavailable.")
    launcher = _headless_launcher(soffice)
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".lo_pdfa_", dir=output_root) as temp_dir:
        profile_uri = _libreoffice_profile_uri()
        filter_value = 'pdf:draw_pdf_Export:{"SelectPdfVersion":{"type":"long","value":"1"}}'
        completed = subprocess.run(
            [str(launcher), "--headless", f"-env:UserInstallation={profile_uri}", "--convert-to", filter_value, "--outdir", temp_dir, str(source)],
            capture_output=True, text=True, timeout=timeout_seconds, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        generated = Path(temp_dir) / f"{source.stem}.pdf"
        if completed.returncode or not generated.exists():
            raise RuntimeError((completed.stderr or completed.stdout or "PDF/A export failed.").strip())
        output = safe_output_path(output_root, f"{source.stem}_pdfa", ".pdf")
        shutil.move(str(generated), output)
        return output

