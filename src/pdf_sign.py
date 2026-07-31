"""Place a personal signature image on a PDF.

This is a visible signature, the same idea as signing a printout by hand. It is not a
cryptographic digital signature and makes no legal certification claim.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from .choices import match_choice
from .output_paths import safe_output_path
from .pdf_annotate import IMAGE_SUFFIXES, _image_stream
from .pdf_edit import MM_TO_POINTS
from .pdf_tools import open_document, parse_page_list
from .tool_result import ToolOutput


PLACEMENTS = (
    "Bottom right",
    "Bottom left",
    "Bottom center",
    "Top right",
    "Top left",
    "Custom position",
)


def _target_rect(
    placement: str,
    page: fitz.Page,
    width: float,
    height: float,
    margin: float,
    x_mm: float,
    y_mm: float,
) -> fitz.Rect:
    if placement == "Custom position":
        left, top = float(x_mm) * MM_TO_POINTS, float(y_mm) * MM_TO_POINTS
        return fitz.Rect(left, top, left + width, top + height)

    vertical, horizontal = placement.split(" ", 1)
    top = margin if vertical == "Top" else page.rect.height - margin - height
    if horizontal.lower() == "left":
        left = margin
    elif horizontal.lower() == "right":
        left = page.rect.width - margin - width
    else:
        left = (page.rect.width - width) / 2
    return fitz.Rect(left, top, left + width, top + height)


def sign_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    signature_image: str | Path | None = None,
    placement: str = "Bottom right",
    width_mm: float = 45.0,
    margin_mm: float = 15.0,
    x_mm: float = 20.0,
    y_mm: float = 240.0,
    opacity: float = 1.0,
    signed_by: str = "",
    sign_date: str = "",
    pages: str | None = "",
    password: str | None = None,
) -> ToolOutput:
    """Stamp a signature image, optionally with a name and date caption."""
    if not signature_image:
        raise ValueError("Choose a signature image, or draw one first.")
    image_path = Path(signature_image).expanduser()
    if not image_path.is_file():
        raise ValueError(f"Signature image was not found: {image_path}")
    if image_path.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError("The signature must be a PNG, JPG or JPEG file.")

    spot = match_choice(placement, PLACEMENTS, "a signature position")
    if not 10 <= float(width_mm) <= 150:
        raise ValueError("Choose a signature width between 10 and 150 mm.")
    if not 0 <= float(margin_mm) <= 100:
        raise ValueError("Choose a margin between 0 and 100 mm.")

    stream, ratio = _image_stream(image_path, float(opacity))
    width = float(width_mm) * MM_TO_POINTS
    height = width * ratio
    margin = float(margin_mm) * MM_TO_POINTS
    caption = " ".join(part for part in [(signed_by or "").strip(), (sign_date or "").strip()] if part)

    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_signed", ".pdf")

    document = open_document(source, password)
    try:
        # A blank page list signs only the last page, which is the usual place to sign.
        if pages is None or not str(pages).strip():
            selected = [document.page_count - 1]
        else:
            selected = parse_page_list(str(pages), document.page_count)

        for page_index in selected:
            page = document.load_page(page_index)
            target = _target_rect(spot, page, width, height, margin, x_mm, y_mm)
            if not target.intersects(page.rect):
                raise ValueError(
                    f"The signature would fall outside page {page_index + 1}. "
                    "Use a smaller width or a standard position."
                )
            page.insert_image(target, stream=stream, overlay=True, keep_proportion=True)
            if caption:
                page.insert_text(
                    fitz.Point(target.x0, min(target.y1 + 10, page.rect.height - 4)),
                    caption,
                    fontname="helv",
                    fontsize=8,
                    color=(0.25, 0.25, 0.25),
                    overlay=True,
                )
        document.save(str(output_path), garbage=3, deflate=True)
        signed_pages = len(selected)
    finally:
        document.close()

    note = f"Signed {signed_pages} page(s); visible signature, not a certified digital signature"
    return ToolOutput([output_path], note)
