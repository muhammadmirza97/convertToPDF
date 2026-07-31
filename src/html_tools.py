"""HTML to PDF conversion using the local PyMuPDF story renderer.

This handles simple documents: headings, paragraphs, lists, tables, links, basic CSS and
local images. It is not a browser engine, so JavaScript, flexbox, grid and remote assets
are ignored.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from .choices import match_choice
from .image_tools import MM_TO_POINTS
from .output_paths import safe_output_path


PAGE_SIZES = ("A4", "Letter", "Legal", "A3", "A5")
ORIENTATIONS = ("Portrait", "Landscape")


def _read_html(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def html_to_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    page_size: str = "A4",
    orientation: str = "Portrait",
    margin_mm: float = 18.0,
) -> Path:
    source = Path(input_path)
    label = match_choice(page_size, PAGE_SIZES, "a page size")
    wanted = match_choice(orientation, ORIENTATIONS, "an orientation")
    if not 0 <= float(margin_mm) <= 60:
        raise ValueError("Choose a margin between 0 and 60 mm.")

    rect = fitz.paper_rect(label.lower())
    if wanted == "Landscape":
        rect = fitz.Rect(0, 0, rect.height, rect.width)
    margin = float(margin_mm) * MM_TO_POINTS
    area = fitz.Rect(margin, margin, rect.width - margin, rect.height - margin)
    if area.width <= 0 or area.height <= 0:
        raise ValueError("The margin is larger than the page. Use a smaller margin.")

    html = _read_html(source)
    output_path = safe_output_path(output_dir, source.stem, ".pdf")

    try:
        archive = fitz.Archive(str(source.parent))
        story = fitz.Story(html=html, archive=archive)
        writer = fitz.DocumentWriter(str(output_path))
        page_limit = 2000
        pages = 0
        more = True
        while more and pages < page_limit:
            device = writer.begin_page(rect)
            more, _filled = story.place(area)
            story.draw(device)
            writer.end_page()
            pages += 1
        writer.close()
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise ValueError(f"{source.name} could not be rendered as a PDF: {exc}") from exc

    if pages >= page_limit:
        output_path.unlink(missing_ok=True)
        raise ValueError(f"{source.name} is too large to render (over {page_limit} pages).")
    return output_path
