"""PDF tools built on local Python libraries."""

from __future__ import annotations

import difflib
import io
import os
import shutil
from pathlib import Path
from typing import Iterable, Sequence

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


def pdf_to_images(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    image_format: str = "png",
    dpi: int = 150,
    jpeg_quality: int = 90,
) -> list[Path]:
    """Render PDF pages to PNG or JPEG images."""
    fmt = image_format.lower().replace("jpeg", "jpg")
    if fmt not in {"png", "jpg"}:
        raise ValueError("Image format must be PNG or JPG.")
    source = Path(input_path)
    zoom = dpi / 72
    outputs: list[Path] = []
    with fitz.open(source) as document:
        if document.needs_pass:
            raise ValueError(f"Encrypted PDF needs password support: {source.name}")
        folder = derived_folder(output_dir, f"{source.stem}_{fmt}")
        for page_number, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            output = safe_output_path(folder, f"{source.stem}_page_{page_number:03d}", f".{fmt}")
            if fmt == "jpg":
                pixmap.save(output, jpg_quality=max(1, min(100, jpeg_quality)))
            else:
                pixmap.save(output)
            outputs.append(output)
    return outputs


def organize_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    page_order: Sequence[int] | None = None,
    insert_paths: Sequence[str | Path] | None = None,
) -> Path:
    """Reorder/delete pages using a zero-based page list, then append inserts."""
    source = Path(input_path)
    reader = _reader(source)
    order = list(range(len(reader.pages))) if page_order is None else list(page_order)
    if any(index < 0 or index >= len(reader.pages) for index in order):
        raise ValueError("Page order contains a page outside this PDF.")
    writer = PdfWriter()
    writer.append(reader, pages=order)
    for insert_path in insert_paths or []:
        writer.append(_reader(insert_path))
    output = safe_output_path(output_dir, f"{source.stem}_organized", ".pdf")
    with output.open("wb") as handle:
        writer.write(handle)
    return output


def rotate_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    degrees: int = 90,
    page_ranges: str | None = None,
) -> Path:
    if degrees not in {90, 180, 270}:
        raise ValueError("Rotation must be 90, 180, or 270 degrees.")
    source = Path(input_path)
    reader = _reader(source)
    selected = {
        index
        for start, end in parse_page_ranges(page_ranges, len(reader.pages))
        for index in range(start, end + 1)
    } if page_ranges else set(range(len(reader.pages)))
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        if index in selected:
            page.rotate(degrees)
        writer.add_page(page)
    output = safe_output_path(output_dir, f"{source.stem}_rotated", ".pdf")
    with output.open("wb") as handle:
        writer.write(handle)
    return output


def compress_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    preset: str = "medium",
) -> Path:
    """Compress streams and downsample raster pages for medium/high presets."""
    source = Path(input_path)
    preset_key = preset.lower()
    if preset_key not in {"low", "medium", "high"}:
        raise ValueError("Compression preset must be low, medium, or high.")
    output = safe_output_path(output_dir, f"{source.stem}_compressed", ".pdf")
    dpi = {"low": 144, "medium": 110, "high": 80}[preset_key]
    quality = {"low": 85, "medium": 68, "high": 48}[preset_key]
    with fitz.open(source) as document:
        if document.needs_pass:
            raise ValueError("Unlock the PDF before compressing it.")
        document.rewrite_images(dpi_threshold=dpi + 1, dpi_target=dpi, quality=quality)
        document.save(output, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True)
    return output


def repair_pdf(input_path: str | Path, output_dir: str | Path) -> Path:
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_repaired", ".pdf")
    try:
        with fitz.open(source) as document:
            document.save(output, garbage=4, clean=True, deflate=True)
    except Exception:
        reader = PdfReader(str(source), strict=False)
        writer = PdfWriter()
        failures: list[int] = []
        for number, page in enumerate(reader.pages, start=1):
            try:
                writer.add_page(page)
            except Exception:
                failures.append(number)
        if not writer.pages:
            raise ValueError("No recoverable pages were found.")
        with output.open("wb") as handle:
            writer.write(handle)
        if failures:
            report = safe_output_path(output_dir, f"{source.stem}_repair_report", ".txt")
            report.write_text(
                "Unrecoverable pages: " + ", ".join(map(str, failures)), encoding="utf-8"
            )
    return output


def watermark_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    text: str = "CONFIDENTIAL",
    image_path: str | Path | None = None,
    position: str = "center",
    rotation: int = 0,
    opacity: float = 0.25,
) -> Path:
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_watermarked", ".pdf")
    positions = {
        "top-left": (0.08, 0.12), "top": (0.5, 0.12), "top-right": (0.92, 0.12),
        "left": (0.08, 0.5), "center": (0.5, 0.5), "right": (0.92, 0.5),
        "bottom-left": (0.08, 0.88), "bottom": (0.5, 0.88), "bottom-right": (0.92, 0.88),
    }
    if position not in positions:
        raise ValueError("Choose a valid watermark position.")
    with fitz.open(source) as document:
        for page in document:
            x_ratio, y_ratio = positions[position]
            point = fitz.Point(page.rect.width * x_ratio, page.rect.height * y_ratio)
            if image_path:
                width = page.rect.width * 0.28
                rect = fitz.Rect(point.x - width / 2, point.y - width / 4, point.x + width / 2, point.y + width / 4)
                page.insert_image(rect, filename=str(image_path), overlay=True)
            else:
                page.insert_text(
                    point, text, fontsize=max(14, page.rect.width / 16), rotate=rotation,
                    fill_opacity=max(0.0, min(1.0, opacity)), overlay=True,
                )
        document.save(output, garbage=4, deflate=True)
    return output


def add_page_numbers(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    position: str = "bottom-center",
    start_number: int = 1,
    include_total: bool = False,
) -> Path:
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_numbered", ".pdf")
    with fitz.open(source) as document:
        total = len(document)
        for index, page in enumerate(document):
            number = start_number + index
            label = f"{number} of {start_number + total - 1}" if include_total else str(number)
            top = position.startswith("top")
            align = 0 if position.endswith("left") else 2 if position.endswith("right") else 1
            y = 18 if top else page.rect.height - 32
            page.insert_textbox(fitz.Rect(36, y, page.rect.width - 36, y + 18), label, fontsize=10, align=align)
        document.save(output, garbage=4, deflate=True)
    return output


def crop_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    rect: Sequence[float],
    pages: Iterable[int] | None = None,
) -> Path:
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_cropped", ".pdf")
    crop = fitz.Rect(*rect)
    selected = set(pages) if pages is not None else None
    with fitz.open(source) as document:
        for index, page in enumerate(document):
            if selected is None or index in selected:
                if not page.mediabox.contains(crop) or crop.is_empty:
                    raise ValueError("Crop rectangle must be inside the page.")
                page.set_cropbox(crop)
        document.save(output)
    return output


def protect_pdf(input_path: str | Path, output_dir: str | Path, *, password: str) -> Path:
    if not password:
        raise ValueError("Enter a password.")
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_protected", ".pdf")
    with fitz.open(source) as document:
        document.save(
            output,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=password,
            owner_pw=password,
            permissions=fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY,
        )
    return output


def unlock_pdf(input_path: str | Path, output_dir: str | Path, *, password: str) -> Path:
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_unlocked", ".pdf")
    with fitz.open(source) as document:
        if not document.needs_pass:
            raise ValueError("This PDF is not encrypted.")
        if document.authenticate(password) == 0:
            raise ValueError("The password is incorrect.")
        document.save(output, encryption=fitz.PDF_ENCRYPT_NONE)
    return output


def redact_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    search_text: str | None = None,
    rectangles: Sequence[Sequence[float]] | None = None,
) -> Path:
    if not search_text and not rectangles:
        raise ValueError("Provide text or rectangles to redact.")
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_redacted", ".pdf")
    with fitz.open(source) as document:
        found = 0
        for page in document:
            targets = list(rectangles or []) + [tuple(rect) for rect in page.search_for(search_text or "")]
            for target in targets:
                page.add_redact_annot(fitz.Rect(*target), fill=(0, 0, 0))
                found += 1
            if targets:
                page.apply_redactions()
        if not found:
            raise ValueError("No matching content was found to redact.")
        document.save(output, garbage=4, clean=True, deflate=True)
    return output


def compare_pdfs(first_path: str | Path, second_path: str | Path, output_dir: str | Path) -> Path:
    def lines(path: str | Path) -> list[str]:
        with fitz.open(path) as document:
            result: list[str] = []
            for number, page in enumerate(document, start=1):
                result.append(f"--- page {number} ---\n")
                result.extend(page.get_text().splitlines(keepends=True))
            return result
    report = "".join(difflib.unified_diff(lines(first_path), lines(second_path), fromfile=Path(first_path).name, tofile=Path(second_path).name))
    output = safe_output_path(output_dir, "pdf_comparison", ".txt")
    output.write_text(report or "No text differences found.\n", encoding="utf-8")
    return output


def sign_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    signature_image: str | Path,
    page_number: int = 1,
    rect: Sequence[float] = (72, 650, 220, 720),
) -> Path:
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_signed", ".pdf")
    with fitz.open(source) as document:
        if page_number < 1 or page_number > len(document):
            raise ValueError("Signature page is outside this PDF.")
        document[page_number - 1].insert_image(fitz.Rect(*rect), filename=str(signature_image), overlay=True)
        document.save(output, deflate=True)
    return output


def edit_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    page_number: int = 1,
    text: str | None = None,
    point: Sequence[float] = (72, 72),
    image_path: str | Path | None = None,
    image_rect: Sequence[float] = (72, 90, 220, 190),
    rectangle: Sequence[float] | None = None,
    ink_points: Sequence[Sequence[float]] | None = None,
) -> Path:
    """Add non-destructive text, image, rectangle, and ink content to a page."""
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_edited", ".pdf")
    with fitz.open(source) as document:
        if page_number < 1 or page_number > len(document):
            raise ValueError("Edit page is outside this PDF.")
        page = document[page_number - 1]
        if text:
            page.insert_text(fitz.Point(*point), text, fontsize=12, overlay=True)
        if image_path:
            page.insert_image(fitz.Rect(*image_rect), filename=str(image_path), overlay=True)
        if rectangle:
            page.draw_rect(fitz.Rect(*rectangle), color=(0.85, 0.1, 0.1), width=2, overlay=True)
        if ink_points:
            page.add_ink_annot([[fitz.Point(*point) for point in ink_points]])
        document.save(output, garbage=4, deflate=True)
    return output


def create_pdf_form(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    field_name: str,
    rect: Sequence[float],
    page_number: int = 1,
    checkbox: bool = False,
) -> Path:
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_form", ".pdf")
    with fitz.open(source) as document:
        page = document[page_number - 1]
        widget = fitz.Widget()
        widget.field_name = field_name
        widget.rect = fitz.Rect(*rect)
        widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX if checkbox else fitz.PDF_WIDGET_TYPE_TEXT
        widget.field_value = "Off" if checkbox else ""
        page.add_widget(widget)
        document.save(output)
    return output


def fill_pdf_form(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    values: dict[str, str | bool],
) -> Path:
    source = Path(input_path)
    reader = _reader(source)
    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, values, auto_regenerate=False)
    output = safe_output_path(output_dir, f"{source.stem}_filled", ".pdf")
    with output.open("wb") as handle:
        writer.write(handle)
    return output


def html_to_pdf(input_path: str | Path, output_dir: str | Path) -> Path:
    """Convert a local HTML file with PyMuPDF Story; URLs are intentionally unsupported."""
    source = Path(input_path)
    if source.suffix.lower() not in {".html", ".htm"}:
        raise ValueError("Choose a local HTML file.")
    html = source.read_text(encoding="utf-8", errors="replace")
    output = safe_output_path(output_dir, source.stem, ".pdf")
    writer = fitz.DocumentWriter(str(output))
    story = fitz.Story(html=html, user_css="body { font-family: sans-serif; font-size: 11pt; }")
    mediabox = fitz.paper_rect("a4")
    content = mediabox + (36, 48, -36, -48)

    def page_rect(_page_number: int, _filled: fitz.Rect) -> tuple[fitz.Rect, fitz.Rect, fitz.Matrix]:
        return mediabox, content, fitz.Identity

    story.write(writer, page_rect)
    writer.close()
    return output


def find_tesseract() -> Path | None:
    candidate = shutil.which("tesseract") or shutil.which("tesseract.exe")
    if candidate:
        return Path(candidate)
    common_paths = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        common_paths.append(Path(local_app_data) / "Programs" / "Tesseract-OCR" / "tesseract.exe")
    return next((path for path in common_paths if path.exists()), None)


def ocr_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    language: str = "eng",
    tesseract_path: str | Path | None = None,
) -> Path:
    executable = Path(tesseract_path) if tesseract_path else find_tesseract()
    if executable is None:
        raise RuntimeError("Tesseract was not found. Install it to enable OCR.")
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("pytesseract is not installed.") from exc
    pytesseract.pytesseract.tesseract_cmd = str(executable)
    source = Path(input_path)
    output = safe_output_path(output_dir, f"{source.stem}_ocr", ".pdf")
    with fitz.open(source) as document:
        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
            x_scale, y_scale = page.rect.width / image.width, page.rect.height / image.height
            for index, value in enumerate(data["text"]):
                word = value.strip()
                if not word:
                    continue
                x = data["left"][index] * x_scale
                y = (data["top"][index] + data["height"][index]) * y_scale
                page.insert_text(
                    (x, y), word, fontsize=max(4, data["height"][index] * y_scale),
                    render_mode=3, overlay=True,
                )
        document.save(output, garbage=4, deflate=True)
    return output


def pdf_to_text(input_path: str | Path, output_dir: str | Path) -> Path:
    source = Path(input_path)
    chunks: list[str] = []

    with fitz.open(source) as document:
        if document.needs_pass:
            raise ValueError(f"Encrypted PDF needs password support: {source.name}")
        output_path = safe_output_path(output_dir, source.stem, ".txt")
        for page_number, page in enumerate(document, start=1):
            chunks.append(f"--- Page {page_number} ---\n")
            chunks.append(page.get_text().strip())
            chunks.append("\n\n")

    output_path.write_text("".join(chunks), encoding="utf-8")
    return output_path
