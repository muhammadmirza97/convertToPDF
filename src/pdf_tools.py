"""PDF tools built on local Python libraries."""

from __future__ import annotations

from pathlib import Path

import fitz
from pypdf import PdfReader, PdfWriter

from .output_paths import derived_folder, safe_output_path


def _reader(path: str | Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        raise ValueError(f"Encrypted PDF needs password support: {Path(path).name}")
    return reader


def merge_pdfs(input_paths: list[str | Path], output_dir: str | Path) -> Path:
    if len(input_paths) < 2:
        raise ValueError("Merge needs at least two PDF files.")

    output_path = safe_output_path(output_dir, "merged", ".pdf")
    writer = PdfWriter()
    for path in input_paths:
        reader = _reader(path)
        for page in reader.pages:
            writer.add_page(page)

    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path


def parse_page_ranges(page_ranges: str | None, page_count: int) -> list[tuple[int, int]]:
    """Parse 1-based page ranges into inclusive zero-based ranges."""
    if page_count < 1:
        raise ValueError("This PDF has no pages to split.")
    if not page_ranges or not page_ranges.strip():
        return [(index, index) for index in range(page_count)]

    ranges: list[tuple[int, int]] = []
    for part in page_ranges.split(","):
        token = part.strip()
        if not token:
            continue
        try:
            if "-" in token:
                start_text, end_text = token.split("-", 1)
                start, end = int(start_text.strip()), int(end_text.strip())
            else:
                start = end = int(token)
        except ValueError as exc:
            raise ValueError("Enter page ranges as numbers, such as 1-3,5.") from exc
        if start < 1 or end < start or end > page_count:
            raise ValueError(f"Page range must be between 1 and {page_count}.")
        ranges.append((start - 1, end - 1))

    if not ranges:
        raise ValueError("Enter a valid page range such as 1-3,5.")
    return ranges


def split_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    page_ranges: str | None = None,
) -> list[Path]:
    source = Path(input_path)
    reader = _reader(source)
    ranges = parse_page_ranges(page_ranges, len(reader.pages))
    outputs: list[Path] = []

    for start, end in ranges:
        writer = PdfWriter()
        for page_index in range(start, end + 1):
            writer.add_page(reader.pages[page_index])

        if start == end:
            base = f"{source.stem}_page_{start + 1:03d}"
        else:
            base = f"{source.stem}_pages_{start + 1:03d}-{end + 1:03d}"
        output_path = safe_output_path(output_dir, base, ".pdf")
        with output_path.open("wb") as handle:
            writer.write(handle)
        outputs.append(output_path)

    return outputs


def pdf_to_png(input_path: str | Path, output_dir: str | Path, *, dpi: int = 150) -> list[Path]:
    source = Path(input_path)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    outputs: list[Path] = []

    with fitz.open(source) as document:
        if document.needs_pass:
            raise ValueError(f"Encrypted PDF needs password support: {source.name}")
        folder = derived_folder(output_dir, f"{source.stem}_png")
        for page_index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            output_path = safe_output_path(folder, f"{source.stem}_page_{page_index:03d}", ".png")
            pixmap.save(output_path)
            outputs.append(output_path)
    return outputs


def pdf_to_text(input_path: str | Path, output_dir: str | Path) -> Path:
    source = Path(input_path)
    output_path = safe_output_path(output_dir, source.stem, ".txt")
    chunks: list[str] = []

    with fitz.open(source) as document:
        if document.needs_pass:
            raise ValueError(f"Encrypted PDF needs password support: {source.name}")
        for page_number, page in enumerate(document, start=1):
            chunks.append(f"--- Page {page_number} ---\n")
            chunks.append(page.get_text().strip())
            chunks.append("\n\n")

    output_path.write_text("".join(chunks), encoding="utf-8")
    return output_path
