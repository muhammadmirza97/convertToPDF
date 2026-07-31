"""PDF presentation edits: watermarks, page numbers and cropping."""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from PIL import Image
from pypdf.generic import RectangleObject

from .choices import match_choice
from .output_paths import safe_output_path
from .pdf_tools import (
    open_document,
    open_reader,
    parse_page_list,
    write_pdf,
    writer_with_metadata,
)


MM_TO_POINTS = 72 / 25.4

COLORS: dict[str, tuple[float, float, float]] = {
    "Gray": (0.5, 0.5, 0.5),
    "Black": (0.0, 0.0, 0.0),
    "Red": (0.8, 0.1, 0.1),
    "Blue": (0.1, 0.3, 0.8),
    "Green": (0.1, 0.5, 0.2),
}

POSITIONS = (
    "Bottom center",
    "Bottom right",
    "Bottom left",
    "Top center",
    "Top right",
    "Top left",
)

NUMBER_FORMATS = {
    "1": "{page}",
    "Page 1": "Page {page}",
    "1 of 10": "{page} of {total}",
    "- 1 -": "- {page} -",
}


def _color(name: str) -> tuple[float, float, float]:
    return COLORS[match_choice(name, COLORS, "a colour")]


def _check_opacity(opacity: float) -> float:
    value = float(opacity)
    if not 0.05 <= value <= 1.0:
        raise ValueError("Choose an opacity between 0.05 and 1.0.")
    return value


def _placement(
    position: str,
    page_rect: fitz.Rect,
    text_width: float,
    font_size: float,
    margin_pt: float,
) -> fitz.Point:
    label = match_choice(position, POSITIONS, "a position")
    vertical, horizontal = label.split(" ", 1)
    horizontal = horizontal.title()
    y = margin_pt + font_size if vertical == "Top" else page_rect.height - margin_pt
    if horizontal == "Left":
        x = margin_pt
    elif horizontal == "Right":
        x = page_rect.width - margin_pt - text_width
    else:
        x = (page_rect.width - text_width) / 2
    return fitz.Point(x, y)


def watermark_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    text: str = "",
    image_file: str | Path | None = None,
    opacity: float = 0.25,
    angle: int = 45,
    font_size: int = 48,
    color: str = "Gray",
    scale: float = 0.5,
    tiled: bool = False,
    pages: str | None = None,
    password: str | None = None,
) -> Path:
    """Stamp text or an image over selected pages, once in the centre or tiled."""
    text = (text or "").strip()
    if bool(text) == bool(image_file):
        raise ValueError("Enter watermark text, or choose a watermark image, but not both.")

    opacity = _check_opacity(opacity)
    try:
        angle = int(angle) % 360
    except (TypeError, ValueError) as exc:
        raise ValueError("Enter the watermark angle in degrees.") from exc

    stream: bytes | None = None
    if image_file:
        stream = _watermark_image_stream(image_file, opacity)
        if not 0.05 <= float(scale) <= 1.0:
            raise ValueError("Choose an image scale between 0.05 and 1.0.")
    else:
        if not 4 <= int(font_size) <= 400:
            raise ValueError("Choose a font size between 4 and 400.")
        rgb = _color(color)

    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_watermarked", ".pdf")
    document = open_document(source, password)
    try:
        selected = parse_page_list(pages, document.page_count)
        font = fitz.Font("helv")
        for page_index in selected:
            page = document.load_page(page_index)
            rect = page.rect
            pivot = fitz.Point(rect.width / 2, rect.height / 2)
            morph = (pivot, fitz.Matrix(angle)) if angle else None

            if stream is not None:
                width = rect.width * float(scale)
                with Image.open(io.BytesIO(stream)) as probe:
                    ratio = probe.height / probe.width
                height = width * ratio
                for centre in _stamp_centres(rect, pivot, width, height, tiled):
                    target = fitz.Rect(
                        centre.x - width / 2,
                        centre.y - height / 2,
                        centre.x + width / 2,
                        centre.y + height / 2,
                    )
                    page.insert_image(
                        target, stream=stream, overlay=True, keep_proportion=True, rotate=0
                    )
            else:
                text_width = font.text_length(text, fontsize=font_size)
                for centre in _stamp_centres(rect, pivot, text_width, font_size * 1.4, tiled):
                    start = fitz.Point(centre.x - text_width / 2, centre.y + font_size / 3)
                    page.insert_text(
                        start,
                        text,
                        fontname="helv",
                        fontsize=font_size,
                        color=rgb,
                        fill_opacity=opacity,
                        stroke_opacity=opacity,
                        morph=(centre, fitz.Matrix(angle)) if angle else None,
                        overlay=True,
                    )
        document.save(str(output_path), garbage=3, deflate=True)
    finally:
        document.close()
    return output_path


def _stamp_centres(
    page_rect: fitz.Rect,
    pivot: fitz.Point,
    stamp_width: float,
    stamp_height: float,
    tiled: bool,
) -> list[fitz.Point]:
    """Return one centre point, or a grid of them when tiling across the page."""
    if not tiled:
        return [pivot]

    step_x = max(stamp_width * 1.6, 40.0)
    step_y = max(stamp_height * 2.0, 40.0)
    columns = max(1, int(page_rect.width // step_x) + 1)
    rows = max(1, int(page_rect.height // step_y) + 1)
    centres: list[fitz.Point] = []
    for row in range(rows):
        for column in range(columns):
            centres.append(
                fitz.Point(
                    step_x * (column + 0.5),
                    step_y * (row + 0.5),
                )
            )
    return centres


def _watermark_image_stream(image_file: str | Path, opacity: float) -> bytes:
    path = Path(image_file).expanduser()
    if not path.is_file():
        raise ValueError(f"Watermark image was not found: {path}")
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError("The watermark image must be a PNG, JPG or JPEG file.")

    with Image.open(path) as opened:
        image = opened.convert("RGBA")
        alpha = image.getchannel("A").point(lambda value: int(value * opacity))
        image.putalpha(alpha)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
    return buffer.getvalue()


def add_page_numbers(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    position: str = "Bottom center",
    number_format: str = "Page 1",
    start_number: int = 1,
    font_size: int = 10,
    color: str = "Black",
    margin_mm: float = 12.0,
    pages: str | None = None,
    password: str | None = None,
) -> Path:
    """Stamp page numbers onto selected pages."""
    template = NUMBER_FORMATS[match_choice(number_format, NUMBER_FORMATS, "a number format")]
    if not 4 <= int(font_size) <= 72:
        raise ValueError("Choose a font size between 4 and 72.")
    try:
        start_number = int(start_number)
    except (TypeError, ValueError) as exc:
        raise ValueError("Enter the starting number as a whole number.") from exc
    if start_number < 0:
        raise ValueError("The starting number cannot be negative.")
    if not 0 <= float(margin_mm) <= 100:
        raise ValueError("Choose a margin between 0 and 100 mm.")

    rgb = _color(color)
    margin_pt = float(margin_mm) * MM_TO_POINTS
    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_numbered", ".pdf")

    document = open_document(source, password)
    try:
        selected = parse_page_list(pages, document.page_count)
        total = len(selected)
        font = fitz.Font("helv")
        for offset, page_index in enumerate(selected):
            label = template.format(page=start_number + offset, total=start_number + total - 1)
            page = document.load_page(page_index)
            width = font.text_length(label, fontsize=font_size)
            point = _placement(position, page.rect, width, font_size, margin_pt)
            page.insert_text(
                point,
                label,
                fontname="helv",
                fontsize=font_size,
                color=rgb,
                overlay=True,
            )
        document.save(str(output_path), garbage=3, deflate=True)
    finally:
        document.close()
    return output_path


def crop_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    top_mm: float = 0.0,
    bottom_mm: float = 0.0,
    left_mm: float = 0.0,
    right_mm: float = 0.0,
    pages: str | None = None,
    password: str | None = None,
) -> Path:
    """Trim margins from selected pages by shrinking the crop box."""
    margins = {
        "top": float(top_mm),
        "bottom": float(bottom_mm),
        "left": float(left_mm),
        "right": float(right_mm),
    }
    for name, value in margins.items():
        if value < 0:
            raise ValueError(f"The {name} margin cannot be negative.")
    if not any(margins.values()):
        raise ValueError("Enter at least one margin to crop, in millimetres.")

    source = Path(input_path)
    reader = open_reader(source, password)
    selected = set(parse_page_list(pages, len(reader.pages)))
    writer = writer_with_metadata(reader)

    for index, page in enumerate(reader.pages):
        if index in selected:
            box = page.cropbox
            left = float(box.left) + margins["left"] * MM_TO_POINTS
            bottom = float(box.bottom) + margins["bottom"] * MM_TO_POINTS
            right = float(box.right) - margins["right"] * MM_TO_POINTS
            top = float(box.top) - margins["top"] * MM_TO_POINTS
            if right - left < 10 or top - bottom < 10:
                raise ValueError(
                    f"Those margins leave nothing visible on page {index + 1}. Use smaller values."
                )
            page.cropbox = RectangleObject((left, bottom, right, top))
        writer.add_page(page)

    return write_pdf(writer, safe_output_path(output_dir, f"{source.stem}_cropped", ".pdf"))
