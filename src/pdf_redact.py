"""True redaction: content is removed from the file, not merely covered."""

from __future__ import annotations

from pathlib import Path

import fitz

from .choices import match_choice
from .output_paths import safe_output_path
from .pdf_edit import COLORS, MM_TO_POINTS
from .pdf_tools import open_document, parse_page_list, search_text_rects
from .tool_result import ToolOutput


AREA_HELP = "Areas use page:left,top,width,height in millimetres, such as 1:20,30,80,10."


def parse_areas(spec: str | None, page_count: int) -> dict[int, list[tuple[float, float, float, float]]]:
    """Parse "1:20,30,80,10; 2:10,10,50,8" into per-page rectangles in points."""
    areas: dict[int, list[tuple[float, float, float, float]]] = {}
    if not spec or not spec.strip():
        return areas

    for chunk in spec.replace("\n", ";").split(";"):
        token = chunk.strip()
        if not token:
            continue
        if ":" not in token:
            raise ValueError(f"Each area needs a page number. {AREA_HELP}")
        page_text, numbers = token.split(":", 1)
        try:
            page_number = int(page_text.strip())
            values = [float(item.strip()) for item in numbers.split(",")]
        except ValueError:
            raise ValueError(f"Areas must be numbers. {AREA_HELP}") from None
        if len(values) != 4:
            raise ValueError(f"Each area needs four numbers. {AREA_HELP}")
        if page_number < 1 or page_number > page_count:
            raise ValueError(f"Area page numbers must be between 1 and {page_count}.")
        left, top, width, height = (value * MM_TO_POINTS for value in values)
        if width <= 0 or height <= 0:
            raise ValueError("Area width and height must be greater than zero.")
        areas.setdefault(page_number - 1, []).append((left, top, left + width, top + height))

    return areas


def redact_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    search_text: str = "",
    areas: str = "",
    case_sensitive: bool = False,
    remove_images: bool = False,
    fill_color: str = "Black",
    replacement_text: str = "",
    pages: str | None = None,
    password: str | None = None,
) -> ToolOutput:
    """Permanently remove matching text, chosen areas, or images from the PDF."""
    search_text = (search_text or "").strip()
    areas = (areas or "").strip()
    if not search_text and not areas and not remove_images:
        raise ValueError(
            "Enter text to redact, an area to redact, or turn on 'Remove all images'."
        )

    rgb = COLORS[match_choice(fill_color, COLORS, "a fill colour")]
    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_redacted", ".pdf")

    document = open_document(source, password)
    marked = 0
    try:
        selected = parse_page_list(pages, document.page_count)
        area_map = parse_areas(areas, document.page_count)

        for page_index in selected:
            page = document.load_page(page_index)

            if search_text:
                for rect in search_text_rects(page, search_text, bool(case_sensitive)):
                    page.add_redact_annot(
                        rect,
                        text=replacement_text or None,
                        fill=rgb,
                        text_color=(1, 1, 1),
                        fontsize=9,
                    )
                    marked += 1

            for rect in area_map.get(page_index, []):
                page.add_redact_annot(fitz.Rect(*rect), fill=rgb)
                marked += 1

            if remove_images:
                for image in page.get_images(full=True):
                    for rect in page.get_image_rects(image[0]):
                        page.add_redact_annot(rect, fill=rgb)
                        marked += 1

            # images=2 rasterises partially covered images so hidden pixels cannot return.
            page.apply_redactions(images=2, graphics=1, text=0)

        if marked == 0:
            raise ValueError(
                f"Nothing matched in {source.name}, so no output was written. "
                "Check the text spelling, the page selection, or the area values."
            )
        document.save(str(output_path), garbage=4, deflate=True, clean=True)
    finally:
        document.close()

    return ToolOutput([output_path], f"Removed {marked} area(s) permanently")
