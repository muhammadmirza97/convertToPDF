"""PDF reading, merging, splitting and export tools built on local libraries."""

from __future__ import annotations

import re
from pathlib import Path

import fitz
from pypdf import PdfReader, PdfWriter

from .output_paths import derived_folder, safe_output_path


ENCRYPTED_MESSAGE = "{name} is password protected. Enter its password, or use Unlock PDF first."


def open_reader(path: str | Path, password: str | None = None) -> PdfReader:
    """Open a PDF with pypdf, raising a friendly error for locked files."""
    source = Path(path)
    try:
        reader = PdfReader(str(source))
    except Exception as exc:  # corrupt or unreadable file
        raise ValueError(
            f"{source.name} could not be read as a PDF. Try Repair PDF first."
        ) from exc

    if reader.is_encrypted:
        if not password:
            raise ValueError(ENCRYPTED_MESSAGE.format(name=source.name))
        if not reader.decrypt(password):
            raise ValueError(f"The password for {source.name} is not correct.")
    if len(reader.pages) < 1:
        raise ValueError(f"{source.name} has no pages.")
    return reader


def open_document(path: str | Path, password: str | None = None) -> fitz.Document:
    """Open a PDF with PyMuPDF. The caller is responsible for closing it."""
    source = Path(path)
    try:
        document = fitz.open(source)
    except Exception as exc:
        raise ValueError(
            f"{source.name} could not be read as a PDF. Try Repair PDF first."
        ) from exc

    if document.needs_pass:
        if not password or not document.authenticate(password):
            document.close()
            if not password:
                raise ValueError(ENCRYPTED_MESSAGE.format(name=source.name))
            raise ValueError(f"The password for {source.name} is not correct.")
    if document.page_count < 1:
        document.close()
        raise ValueError(f"{source.name} has no pages.")
    return document


def writer_with_metadata(reader: PdfReader) -> PdfWriter:
    """Start a writer that keeps the source document information."""
    writer = PdfWriter()
    if reader.metadata:
        writer.add_metadata(reader.metadata)
    return writer


def write_pdf(writer: PdfWriter, output_path: Path) -> Path:
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path


def merge_pdfs(
    input_paths: list[str | Path],
    output_dir: str | Path,
    *,
    password: str | None = None,
) -> Path:
    if len(input_paths) < 2:
        raise ValueError("Merge needs at least two PDF files.")

    output_path = safe_output_path(output_dir, "merged", ".pdf")
    writer = PdfWriter()
    for path in input_paths:
        reader = open_reader(path, password)
        for page in reader.pages:
            writer.add_page(page)

    return write_pdf(writer, output_path)


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


def parse_page_list(page_spec: str | None, page_count: int) -> list[int]:
    """Parse "1-3,5" into an ordered zero-based page list.

    A blank spec means every page. Order is preserved and duplicates are dropped, so
    "3,1" selects page 3 then page 1.
    """
    ordered: list[int] = []
    for start, end in parse_page_ranges(page_spec, page_count):
        for index in range(start, end + 1):
            if index not in ordered:
                ordered.append(index)
    return ordered


def split_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    page_ranges: str | None = None,
    every_n_pages: int = 0,
    password: str | None = None,
) -> list[Path]:
    source = Path(input_path)
    reader = open_reader(source, password)
    page_count = len(reader.pages)

    try:
        chunk = int(every_n_pages or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("Enter the chunk size as a whole number of pages.") from exc
    if chunk < 0:
        raise ValueError("The chunk size cannot be negative.")

    if chunk:
        if page_ranges and page_ranges.strip():
            raise ValueError("Use either page ranges or a fixed chunk size, not both.")
        ranges = [(start, min(start + chunk, page_count) - 1) for start in range(0, page_count, chunk)]
    else:
        ranges = parse_page_ranges(page_ranges, page_count)
    outputs: list[Path] = []

    for start, end in ranges:
        writer = PdfWriter()
        for page_index in range(start, end + 1):
            writer.add_page(reader.pages[page_index])

        if start == end:
            base = f"{source.stem}_page_{start + 1:03d}"
        else:
            base = f"{source.stem}_pages_{start + 1:03d}-{end + 1:03d}"
        outputs.append(write_pdf(writer, safe_output_path(output_dir, base, ".pdf")))

    return outputs


def pdf_to_images(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    image_format: str = "png",
    dpi: int = 150,
    pages: str | None = None,
    jpeg_quality: int = 85,
    grayscale: bool = False,
    password: str | None = None,
) -> list[Path]:
    """Render selected PDF pages to PNG or JPG images."""
    fmt = image_format.strip().lower().lstrip(".")
    if fmt == "jpeg":
        fmt = "jpg"
    if fmt not in {"png", "jpg"}:
        raise ValueError("Choose PNG or JPG for the image format.")
    if not 20 <= dpi <= 600:
        raise ValueError("Choose a DPI between 20 and 600.")
    if not 1 <= jpeg_quality <= 100:
        raise ValueError("Choose a JPG quality between 1 and 100.")

    source = Path(input_path)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    colorspace = fitz.csGRAY if grayscale else fitz.csRGB
    outputs: list[Path] = []

    document = open_document(source, password)
    try:
        selected = parse_page_list(pages, document.page_count)
        folder = derived_folder(output_dir, f"{source.stem}_{fmt}")
        for page_index in selected:
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False, colorspace=colorspace)
            output_path = safe_output_path(
                folder, f"{source.stem}_page_{page_index + 1:03d}", f".{fmt}"
            )
            if fmt == "jpg":
                pixmap.save(output_path, jpg_quality=jpeg_quality)
            else:
                pixmap.save(output_path)
            outputs.append(output_path)
    finally:
        document.close()
    return outputs


def pdf_to_png(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 150,
    password: str | None = None,
) -> list[Path]:
    """Render every page to PNG. Thin wrapper kept for older callers."""
    return pdf_to_images(input_path, output_dir, image_format="png", dpi=dpi, password=password)


def extract_images(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    minimum_pixels: int = 64,
    pages: str | None = None,
    password: str | None = None,
) -> list[Path]:
    """Save the images embedded in the PDF in their original form, without re-rendering."""
    if not 1 <= int(minimum_pixels) <= 5000:
        raise ValueError("Choose a minimum size between 1 and 5000 pixels.")

    source = Path(input_path)
    outputs: list[Path] = []
    seen: set[int] = set()

    document = open_document(source, password)
    try:
        folder = derived_folder(output_dir, f"{source.stem}_images")
        for page_index in parse_page_list(pages, document.page_count):
            page = document.load_page(page_index)
            for image in page.get_images(full=True):
                xref = image[0]
                if xref in seen:
                    continue
                seen.add(xref)
                data = document.extract_image(xref)
                if not data:
                    continue
                if min(data.get("width", 0), data.get("height", 0)) < int(minimum_pixels):
                    continue
                suffix = f".{data.get('ext', 'png')}"
                base = f"{source.stem}_page_{page_index + 1:03d}_img_{len(outputs) + 1:03d}"
                output_path = safe_output_path(folder, base, suffix)
                output_path.write_bytes(data["image"])
                outputs.append(output_path)
    finally:
        document.close()

    if not outputs:
        raise ValueError(
            f"No embedded images of at least {int(minimum_pixels)} pixels were found in "
            f"{source.name}. Use PDF to JPG or PNG to render the pages instead."
        )
    return outputs


def pdf_to_text(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    pages: str | None = None,
    password: str | None = None,
) -> Path:
    source = Path(input_path)
    output_path = safe_output_path(output_dir, source.stem, ".txt")
    chunks: list[str] = []

    document = open_document(source, password)
    try:
        for page_index in parse_page_list(pages, document.page_count):
            chunks.append(f"--- Page {page_index + 1} ---\n")
            chunks.append(document.load_page(page_index).get_text().strip())
            chunks.append("\n\n")
    finally:
        document.close()

    output_path.write_text("".join(chunks), encoding="utf-8")
    return output_path


def search_text_rects(page: fitz.Page, needle: str, case_sensitive: bool = False) -> list[fitz.Rect]:
    """Find a phrase on a page.

    MuPDF's own search is always case-insensitive, so an exact-case search re-reads the
    text inside each hit and keeps only the matches that agree on capitalisation.
    """
    hits = page.search_for(needle)
    if not case_sensitive:
        return hits
    kept: list[fitz.Rect] = []
    for rect in hits:
        found = page.get_textbox(rect) or ""
        if needle in found:
            kept.append(rect)
    return kept


_BULLET_PATTERN = re.compile(r"^\s*([•●▪·*\-–]|\d+[.)])\s+")


def _line_text_and_size(line: dict) -> tuple[str, float]:
    text = "".join(span.get("text", "") for span in line.get("spans", []))
    sizes = [float(span.get("size", 0.0)) for span in line.get("spans", []) if span.get("text", "").strip()]
    return text.strip(), max(sizes) if sizes else 0.0


def _is_bold(line: dict) -> bool:
    spans = [span for span in line.get("spans", []) if span.get("text", "").strip()]
    if not spans:
        return False
    return all("bold" in str(span.get("font", "")).lower() for span in spans)


def pdf_to_markdown(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    pages: str | None = None,
    page_breaks: bool = True,
    password: str | None = None,
) -> Path:
    """Extract text as Markdown, using font size to guess headings.

    This is a best-effort structural guess, not a layout-faithful conversion. Tables,
    columns and images are not reconstructed.
    """
    source = Path(input_path)
    output_path = safe_output_path(output_dir, source.stem, ".md")
    lines: list[tuple[str, float, bool]] = []
    page_markers: list[int] = []

    document = open_document(source, password)
    try:
        for page_index in parse_page_list(pages, document.page_count):
            page_markers.append(len(lines))
            page_dict = document.load_page(page_index).get_text("dict")
            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    text, size = _line_text_and_size(line)
                    if text:
                        lines.append((text, size, _is_bold(line)))
    finally:
        document.close()

    if not lines:
        raise ValueError(
            f"No text was found in {source.name}. It may be a scanned PDF, which needs OCR."
        )

    sizes = sorted(size for _text, size, _bold in lines)
    body_size = sizes[len(sizes) // 2] or 1.0

    parts: list[str] = []
    for index, (text, size, bold) in enumerate(lines):
        if page_breaks and index in page_markers and parts:
            parts.append("\n---\n")
        ratio = size / body_size
        if ratio >= 1.6:
            parts.append(f"# {text}")
        elif ratio >= 1.3:
            parts.append(f"## {text}")
        elif ratio >= 1.12 or (bold and ratio >= 1.0 and len(text) < 80):
            parts.append(f"### {text}")
        elif _BULLET_PATTERN.match(text):
            parts.append(f"- {_BULLET_PATTERN.sub('', text)}")
        else:
            parts.append(text)

    output_path.write_text("\n\n".join(parts).strip() + "\n", encoding="utf-8")
    return output_path
