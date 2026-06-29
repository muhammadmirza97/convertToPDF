from __future__ import annotations

from PIL import Image

from src.image_tools import image_to_pdf, images_to_single_pdf


def _make_image(path, color):
    image = Image.new("RGB", (80, 60), color)
    image.save(path)


def test_image_to_pdf_creates_pdf(workspace):
    source = workspace / "photo.png"
    _make_image(source, "navy")

    output = image_to_pdf(source, workspace)

    assert output.exists()
    assert output.suffix == ".pdf"
    assert output.read_bytes().startswith(b"%PDF")


def test_images_to_single_pdf_creates_combined_pdf(workspace):
    first = workspace / "first.jpg"
    second = workspace / "second.jpg"
    _make_image(first, "red")
    _make_image(second, "green")

    output = images_to_single_pdf([first, second], workspace)

    assert output.exists()
    assert output.read_bytes().startswith(b"%PDF")

