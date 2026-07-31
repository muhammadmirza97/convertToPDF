"""PDF editing: highlight text, add text, draw shapes and place images.

Positions are given in millimetres measured from the top-left corner of the page, which is
how a ruler in a word processor behaves.
"""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from PIL import Image

from .choices import match_choice
from .output_paths import safe_output_path
from .pdf_edit import COLORS, MM_TO_POINTS
from .pdf_tools import open_document, parse_page_list, search_text_rects
from .tool_result import ToolOutput


MARK_STYLES = ("Highlight", "Underline", "Strikeout", "Squiggly")
SHAPES = ("Rectangle", "Ellipse", "Line", "Arrow")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def _point(x_mm: float, y_mm: float) -> fitz.Point:
    return fitz.Point(float(x_mm) * MM_TO_POINTS, float(y_mm) * MM_TO_POINTS)


def _rect(x_mm: float, y_mm: float, width_mm: float, height_mm: float) -> fitz.Rect:
    if float(width_mm) <= 0 or float(height_mm) <= 0:
        raise ValueError("Width and height must be greater than zero.")
    start = _point(x_mm, y_mm)
    return fitz.Rect(
        start.x,
        start.y,
        start.x + float(width_mm) * MM_TO_POINTS,
        start.y + float(height_mm) * MM_TO_POINTS,
    )


def _check_inside(rect: fitz.Rect, page: fitz.Page, page_number: int) -> None:
    if not rect.intersects(page.rect):
        raise ValueError(
            f"That position is completely outside page {page_number}, which is "
            f"{page.rect.width / MM_TO_POINTS:.0f} by {page.rect.height / MM_TO_POINTS:.0f} mm."
        )


def highlight_text(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    search_text: str = "",
    style: str = "Highlight",
    color: str = "Red",
    case_sensitive: bool = False,
    pages: str | None = None,
    password: str | None = None,
) -> ToolOutput:
    """Mark every occurrence of a phrase with a highlight, underline or strikeout."""
    search_text = (search_text or "").strip()
    if not search_text:
        raise ValueError("Enter the text you want to mark.")
    wanted = match_choice(style, MARK_STYLES, "a mark style")
    rgb = COLORS[match_choice(color, COLORS, "a colour")]

    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_marked", ".pdf")
    adders = {
        "Highlight": "add_highlight_annot",
        "Underline": "add_underline_annot",
        "Strikeout": "add_strikeout_annot",
        "Squiggly": "add_squiggly_annot",
    }

    document = open_document(source, password)
    marked = 0
    try:
        for page_index in parse_page_list(pages, document.page_count):
            page = document.load_page(page_index)
            for rect in search_text_rects(page, search_text, bool(case_sensitive)):
                annotation = getattr(page, adders[wanted])(rect)
                annotation.set_colors(stroke=rgb)
                annotation.update()
                marked += 1
        if marked == 0:
            raise ValueError(
                f"'{search_text}' was not found in {source.name}. "
                "Scanned PDFs need OCR before their text can be searched."
            )
        document.save(str(output_path), garbage=3, deflate=True)
    finally:
        document.close()

    return ToolOutput([output_path], f"Marked {marked} occurrence(s)")


def add_text(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    text: str = "",
    x_mm: float = 20.0,
    y_mm: float = 20.0,
    font_size: int = 12,
    color: str = "Black",
    pages: str | None = None,
    password: str | None = None,
) -> Path:
    """Draw a line or block of text onto selected pages."""
    text = (text or "").strip()
    if not text:
        raise ValueError("Enter the text you want to add.")
    if not 4 <= int(font_size) <= 200:
        raise ValueError("Choose a font size between 4 and 200.")
    rgb = COLORS[match_choice(color, COLORS, "a colour")]

    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_edited", ".pdf")
    lines = text.replace("\\n", "\n").splitlines() or [text]

    document = open_document(source, password)
    try:
        for page_index in parse_page_list(pages, document.page_count):
            page = document.load_page(page_index)
            start = _point(x_mm, y_mm)
            _check_inside(fitz.Rect(start, start + (1, 1)), page, page_index + 1)
            for offset, line in enumerate(lines):
                point = fitz.Point(start.x, start.y + offset * int(font_size) * 1.3)
                page.insert_text(
                    point, line, fontname="helv", fontsize=int(font_size), color=rgb, overlay=True
                )
        document.save(str(output_path), garbage=3, deflate=True)
    finally:
        document.close()
    return output_path


def add_shape(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    shape: str = "Rectangle",
    x_mm: float = 20.0,
    y_mm: float = 20.0,
    width_mm: float = 60.0,
    height_mm: float = 30.0,
    line_width: float = 1.5,
    color: str = "Red",
    fill: bool = False,
    pages: str | None = None,
    password: str | None = None,
) -> Path:
    """Draw a rectangle, ellipse, line or arrow onto selected pages."""
    wanted = match_choice(shape, SHAPES, "a shape")
    rgb = COLORS[match_choice(color, COLORS, "a colour")]
    if not 0.1 <= float(line_width) <= 20:
        raise ValueError("Choose a line width between 0.1 and 20.")

    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_shapes", ".pdf")

    document = open_document(source, password)
    try:
        for page_index in parse_page_list(pages, document.page_count):
            page = document.load_page(page_index)
            rect = _rect(x_mm, y_mm, width_mm, height_mm)
            _check_inside(rect, page, page_index + 1)
            drawing = page.new_shape()
            if wanted == "Rectangle":
                drawing.draw_rect(rect)
            elif wanted == "Ellipse":
                drawing.draw_oval(rect)
            else:
                start, end = rect.tl, rect.br
                drawing.draw_line(start, end)
                if wanted == "Arrow":
                    _draw_arrow_head(drawing, start, end, float(line_width))
            drawing.finish(
                color=rgb,
                fill=rgb if fill and wanted in ("Rectangle", "Ellipse") else None,
                width=float(line_width),
            )
            drawing.commit()
        document.save(str(output_path), garbage=3, deflate=True)
    finally:
        document.close()
    return output_path


def _draw_arrow_head(drawing, start: fitz.Point, end: fitz.Point, line_width: float) -> None:
    length = max(6.0, line_width * 5)
    direction = fitz.Point(end.x - start.x, end.y - start.y)
    size = max(abs(direction.x), abs(direction.y)) or 1.0
    unit = fitz.Point(direction.x / size, direction.y / size)
    left = fitz.Point(end.x - length * (unit.x + unit.y), end.y - length * (unit.y - unit.x))
    right = fitz.Point(end.x - length * (unit.x - unit.y), end.y - length * (unit.y + unit.x))
    drawing.draw_line(end, left)
    drawing.draw_line(end, right)


def add_image(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    image_file: str | Path | None = None,
    x_mm: float = 20.0,
    y_mm: float = 20.0,
    width_mm: float = 50.0,
    opacity: float = 1.0,
    pages: str | None = None,
    password: str | None = None,
) -> Path:
    """Place an image at a chosen position, keeping its aspect ratio."""
    if not image_file:
        raise ValueError("Choose the image you want to place.")
    image_path = Path(image_file).expanduser()
    if not image_path.is_file():
        raise ValueError(f"Image was not found: {image_path}")
    if image_path.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError("The image must be a PNG, JPG or JPEG file.")
    if not 0.05 <= float(opacity) <= 1.0:
        raise ValueError("Choose an opacity between 0.05 and 1.0.")

    stream, ratio = _image_stream(image_path, float(opacity))
    width = float(width_mm) * MM_TO_POINTS
    if width <= 0:
        raise ValueError("Width must be greater than zero.")

    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_with_image", ".pdf")

    document = open_document(source, password)
    try:
        for page_index in parse_page_list(pages, document.page_count):
            page = document.load_page(page_index)
            start = _point(x_mm, y_mm)
            target = fitz.Rect(start.x, start.y, start.x + width, start.y + width * ratio)
            _check_inside(target, page, page_index + 1)
            page.insert_image(target, stream=stream, overlay=True, keep_proportion=True)
        document.save(str(output_path), garbage=3, deflate=True)
    finally:
        document.close()
    return output_path


def _image_stream(image_path: Path, opacity: float) -> tuple[bytes, float]:
    """Return PNG bytes with the requested opacity, plus the height/width ratio."""
    with Image.open(image_path) as opened:
        image = opened.convert("RGBA")
        if opacity < 1.0:
            alpha = image.getchannel("A").point(lambda value: int(value * opacity))
            image.putalpha(alpha)
        ratio = image.height / image.width
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
    return buffer.getvalue(), ratio
