"""Image to PDF conversion with page layout options."""

from __future__ import annotations

import io
from pathlib import Path

import fitz
from PIL import Image, ImageOps

from .choices import match_choice
from .output_paths import safe_output_path


MM_TO_POINTS = 72 / 25.4

PAGE_SIZES = ("Match image size", "A4", "Letter", "Legal", "A3", "A5")
ORIENTATIONS = ("Auto", "Portrait", "Landscape")
FIT_MODES = ("Fit inside page", "Stretch to page")


def _open_rgb_image(path: str | Path) -> Image.Image:
    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        background = Image.new("RGB", image.size, "white")
        background.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
        return background
    return image.convert("RGB")


def _png_stream(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _page_rect(page_size: str, orientation: str, image: Image.Image) -> fitz.Rect:
    size_label = match_choice(page_size, PAGE_SIZES, "a page size")
    if size_label == "Match image size":
        # Treat the image as 96 DPI so a screenshot keeps roughly its on-screen size.
        return fitz.Rect(0, 0, image.width * 0.75, image.height * 0.75)

    rect = fitz.paper_rect(size_label.lower())
    wanted = match_choice(orientation, ORIENTATIONS, "an orientation")
    landscape = wanted == "Landscape" or (wanted == "Auto" and image.width > image.height)
    if landscape:
        rect = fitz.Rect(0, 0, rect.height, rect.width)
    return rect


def images_to_pdf(
    input_paths: list[str | Path],
    output_dir: str | Path,
    *,
    base_name: str = "combined_images",
    page_size: str = "Match image size",
    orientation: str = "Auto",
    fit: str = "Fit inside page",
    margin_mm: float = 0.0,
    single_file: bool = True,
) -> list[Path]:
    """Convert images to PDF, either one combined file or one PDF per image."""
    if not input_paths:
        raise ValueError("Choose at least one image.")
    fit_mode = match_choice(fit, FIT_MODES, "an image fit")
    if not 0 <= float(margin_mm) <= 100:
        raise ValueError("Choose a margin between 0 and 100 mm.")
    margin = float(margin_mm) * MM_TO_POINTS

    def build(paths: list[str | Path], stem: str) -> Path:
        document = fitz.open()
        try:
            for path in paths:
                image = _open_rgb_image(path)
                try:
                    rect = _page_rect(page_size, orientation, image)
                    page = document.new_page(width=rect.width, height=rect.height)
                    target = fitz.Rect(
                        margin, margin, rect.width - margin, rect.height - margin
                    )
                    if target.width <= 0 or target.height <= 0:
                        raise ValueError("The margin is larger than the page. Use a smaller margin.")
                    page.insert_image(
                        target,
                        stream=_png_stream(image),
                        keep_proportion=fit_mode == "Fit inside page",
                    )
                finally:
                    image.close()
            output_path = safe_output_path(output_dir, stem, ".pdf")
            document.save(str(output_path), deflate=True, garbage=3)
        finally:
            document.close()
        return output_path

    if single_file:
        return [build(list(input_paths), base_name)]
    return [build([path], Path(path).stem) for path in input_paths]


def image_to_pdf(input_path: str | Path, output_dir: str | Path, **options) -> Path:
    """Convert one image to a one-page PDF."""
    source = Path(input_path)
    options.pop("single_file", None)
    options.pop("base_name", None)
    return images_to_pdf([source], output_dir, base_name=source.stem, single_file=True, **options)[0]


def images_to_single_pdf(
    input_paths: list[str | Path],
    output_dir: str | Path,
    *,
    base_name: str = "combined_images",
    **options,
) -> Path:
    """Combine several images into one PDF."""
    options.pop("single_file", None)
    return images_to_pdf(input_paths, output_dir, base_name=base_name, single_file=True, **options)[0]
