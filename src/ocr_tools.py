"""Local OCR for scanned PDFs, using Tesseract through PyMuPDF.

The scanned page image is kept exactly as it was; an invisible text layer is added on top
so the PDF becomes searchable and selectable.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import fitz

from .output_paths import safe_output_path
from .pdf_tools import open_document
from .tool_result import ToolOutput


COMMON_WINDOWS_TESSERACT_PATHS = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]


def find_tesseract() -> Path | None:
    """Locate the Tesseract executable, or return None."""
    found = shutil.which("tesseract") or shutil.which("tesseract.exe")
    if found:
        return Path(found)
    for candidate in COMMON_WINDOWS_TESSERACT_PATHS:
        if candidate.exists():
            return candidate
    return None


def find_tessdata() -> Path | None:
    """Locate the tessdata folder holding language files."""
    from_env = os.environ.get("TESSDATA_PREFIX")
    if from_env:
        candidate = Path(from_env)
        if (candidate / "eng.traineddata").is_file():
            return candidate
        if (candidate / "tessdata" / "eng.traineddata").is_file():
            return candidate / "tessdata"

    executable = find_tesseract()
    if executable:
        candidate = executable.parent / "tessdata"
        if candidate.is_dir():
            return candidate
    return None


def available_languages() -> list[str]:
    """List the installed Tesseract language codes."""
    tessdata = find_tessdata()
    if not tessdata:
        return []
    codes = sorted(path.stem for path in tessdata.glob("*.traineddata") if path.stem != "osd")
    return codes


def _require_ocr() -> Path:
    tessdata = find_tessdata()
    if not find_tesseract() or not tessdata:
        raise RuntimeError(
            "Tesseract OCR was not found. Install Tesseract, then restart the app."
        )
    return tessdata


def page_has_text(page: fitz.Page, minimum_characters: int = 12) -> bool:
    return len(page.get_text().strip()) >= minimum_characters


def ocr_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    language: str = "eng",
    dpi: int = 300,
    skip_pages_with_text: bool = True,
    pages: str | None = None,
    password: str | None = None,
) -> ToolOutput:
    """Write a searchable copy of a scanned PDF."""
    tessdata = _require_ocr()
    language = (language or "eng").strip() or "eng"
    installed = available_languages()
    for code in language.split("+"):
        if code and installed and code not in installed:
            raise ValueError(
                f"Language pack '{code}' is not installed. Available: {', '.join(installed)}."
            )
    if not 72 <= int(dpi) <= 600:
        raise ValueError("Choose an OCR resolution between 72 and 600 DPI.")

    from .pdf_tools import parse_page_list

    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_searchable", ".pdf")
    zoom = int(dpi) / 72
    matrix = fitz.Matrix(zoom, zoom)

    document = open_document(source, password)
    result = fitz.open()
    recognized = 0
    skipped = 0
    try:
        selected = set(parse_page_list(pages, document.page_count))
        for index in range(document.page_count):
            page = document.load_page(index)
            if index not in selected or (skip_pages_with_text and page_has_text(page)):
                result.insert_pdf(document, from_page=index, to_page=index)
                skipped += 1
                continue

            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            try:
                ocr_bytes = pixmap.pdfocr_tobytes(language=language, tessdata=str(tessdata))
            except Exception as exc:
                raise ValueError(f"OCR failed on page {index + 1} of {source.name}: {exc}") from exc
            with fitz.open("pdf", ocr_bytes) as ocr_page:
                result.insert_pdf(ocr_page)
            recognized += 1

        if recognized == 0:
            result.close()
            raise ValueError(
                f"Every page of {source.name} already has text. "
                "Turn off 'Skip pages that already have text' to OCR them anyway."
            )
        result.save(str(output_path), garbage=3, deflate=True)
    finally:
        document.close()
        if not result.is_closed:
            result.close()

    note = f"OCR ran on {recognized} page(s); {skipped} page(s) kept as they were"
    return ToolOutput([output_path], note)
