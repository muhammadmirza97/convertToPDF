"""Best-effort export from PDF to Excel and PowerPoint, using local libraries only.

PDF has no reliable notion of tables or slides, so these conversions reconstruct a useful
approximation rather than a faithful original document.
"""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.util import Emu

from .output_paths import safe_output_path
from .pdf_tools import open_document, parse_page_list
from .tool_result import ToolOutput


EXCEL_MODES = ("Detected tables", "Text lines")
EMU_PER_POINT = 12700


def _clean(value) -> str:
    return "" if value is None else str(value).replace("\n", " ").strip()


def _find_tables(page: fitz.Page) -> list:
    """Look for ruled tables first, then fall back to whitespace-aligned columns."""
    for strategy in ("lines", "text"):
        try:
            found = list(page.find_tables(strategy=strategy))
        except Exception:
            continue
        if found:
            return found
    return []


def pdf_to_excel(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    mode: str = "Detected tables",
    pages: str | None = None,
    password: str | None = None,
) -> ToolOutput:
    """Write detected tables, or plain text lines, into an .xlsx workbook."""
    from .choices import match_choice

    wanted = match_choice(mode, EXCEL_MODES, "an Excel export mode")
    source = Path(input_path)
    output_path = safe_output_path(output_dir, source.stem, ".xlsx")

    workbook = Workbook()
    workbook.remove(workbook.active)
    document = open_document(source, password)
    tables_found = 0
    try:
        selected = parse_page_list(pages, document.page_count)
        for page_index in selected:
            page = document.load_page(page_index)
            if wanted == "Detected tables":
                found = _find_tables(page)
                for table_number, table in enumerate(found, start=1):
                    rows = table.extract()
                    if not rows:
                        continue
                    tables_found += 1
                    title = f"p{page_index + 1}_table{table_number}"[:31]
                    sheet = workbook.create_sheet(title)
                    for row in rows:
                        sheet.append([_clean(cell) for cell in row])
                    _autosize(sheet)
            else:
                lines = [line for line in page.get_text().splitlines() if line.strip()]
                if not lines:
                    continue
                tables_found += 1
                sheet = workbook.create_sheet(f"page_{page_index + 1}"[:31])
                for line in lines:
                    sheet.append([line])
                _autosize(sheet)

        if tables_found == 0:
            hint = (
                "No tables were detected. Try the 'Text lines' mode instead."
                if wanted == "Detected tables"
                else "No text was found. A scanned PDF needs OCR first."
            )
            raise ValueError(f"{source.name}: {hint}")
        workbook.save(output_path)
    finally:
        document.close()
        workbook.close()

    label = "table" if wanted == "Detected tables" else "page"
    return ToolOutput([output_path], f"Wrote {tables_found} {label}(s) as worksheets")


def _autosize(sheet, limit: int = 60) -> None:
    widths: dict[int, int] = {}
    for row in sheet.iter_rows():
        for cell in row:
            if cell.value:
                widths[cell.column] = min(limit, max(widths.get(cell.column, 10), len(str(cell.value)) + 2))
    for column, width in widths.items():
        sheet.column_dimensions[get_column_letter(column)].width = width


def pdf_to_powerpoint(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 150,
    include_notes: bool = True,
    pages: str | None = None,
    password: str | None = None,
) -> ToolOutput:
    """Write one slide per PDF page, with the page image and its text in the notes."""
    if not 72 <= int(dpi) <= 400:
        raise ValueError("Choose a slide resolution between 72 and 400 DPI.")

    source = Path(input_path)
    output_path = safe_output_path(output_dir, source.stem, ".pptx")
    zoom = int(dpi) / 72
    matrix = fitz.Matrix(zoom, zoom)

    presentation = Presentation()
    blank_layout = presentation.slide_layouts[6]
    document = open_document(source, password)
    slides = 0
    try:
        selected = parse_page_list(pages, document.page_count)
        first_page = document.load_page(selected[0])
        presentation.slide_width = Emu(int(first_page.rect.width * EMU_PER_POINT))
        presentation.slide_height = Emu(int(first_page.rect.height * EMU_PER_POINT))

        for page_index in selected:
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            slide = presentation.slides.add_slide(blank_layout)
            slide.shapes.add_picture(
                io.BytesIO(pixmap.tobytes("png")),
                left=0,
                top=0,
                width=presentation.slide_width,
                height=presentation.slide_height,
            )
            if include_notes:
                text = page.get_text().strip()
                if text:
                    slide.notes_slide.notes_text_frame.text = text
            slides += 1
        presentation.save(output_path)
    finally:
        document.close()

    note = f"Wrote {slides} slide(s), one per page"
    if include_notes:
        note += "; page text is in the speaker notes"
    return ToolOutput([output_path], note)
