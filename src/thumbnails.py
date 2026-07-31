"""Local page thumbnail rendering for the visual Organize workspace."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image

from .pdf_tools import open_document


@dataclass
class PageThumbnail:
    index: int          # zero-based page index in the source PDF
    width: int
    height: int
    png_bytes: bytes

    def to_image(self) -> Image.Image:
        return Image.open(io.BytesIO(self.png_bytes))


def render_thumbnails(
    input_path: str | Path,
    *,
    max_edge: int = 180,
    password: str | None = None,
    limit: int | None = None,
) -> list[PageThumbnail]:
    """Render every page to a small PNG thumbnail, scaled to fit max_edge."""
    if max_edge < 40 or max_edge > 600:
        raise ValueError("Thumbnail size must be between 40 and 600 pixels.")

    document = open_document(input_path, password)
    thumbnails: list[PageThumbnail] = []
    try:
        count = document.page_count if limit is None else min(limit, document.page_count)
        for index in range(count):
            page = document.load_page(index)
            longest = max(page.rect.width, page.rect.height) or 1
            zoom = max_edge / longest
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            thumbnails.append(
                PageThumbnail(index, pixmap.width, pixmap.height, pixmap.tobytes("png"))
            )
    finally:
        document.close()
    return thumbnails
