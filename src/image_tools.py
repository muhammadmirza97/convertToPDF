"""Image conversion tools."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from .output_paths import safe_output_path


def _open_rgb_image(path: str | Path) -> Image.Image:
    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        background = Image.new("RGB", image.size, "white")
        background.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
        return background
    return image.convert("RGB")


def image_to_pdf(input_path: str | Path, output_dir: str | Path) -> Path:
    source = Path(input_path)
    output_path = safe_output_path(output_dir, source.stem, ".pdf")
    image = _open_rgb_image(source)
    try:
        image.save(output_path, "PDF", resolution=100.0)
    finally:
        image.close()
    return output_path


def images_to_single_pdf(
    input_paths: list[str | Path],
    output_dir: str | Path,
    *,
    base_name: str = "combined_images",
) -> Path:
    if not input_paths:
        raise ValueError("Choose at least one image.")

    output_path = safe_output_path(output_dir, base_name, ".pdf")
    opened = [_open_rgb_image(path) for path in input_paths]
    first, rest = opened[0], opened[1:]
    try:
        first.save(output_path, "PDF", resolution=100.0, save_all=True, append_images=rest)
    finally:
        for image in opened:
            image.close()
    return output_path

