from __future__ import annotations

import random

import fitz
import pytest
from PIL import Image

from src.pdf_optimize import compress_pdf, repair_pdf


def _image_pdf(workspace, name="heavy.pdf"):
    """Build a PDF holding one large noisy image, which compresses badly by design."""
    random.seed(7)
    image = Image.new("RGB", (900, 700))
    image.putdata([(random.randint(0, 255),) * 3 for _ in range(900 * 700)])
    image_path = workspace / "noise.png"
    image.save(image_path)

    pdf_path = workspace / name
    document = fitz.open()
    page = document.new_page()
    page.insert_image(page.rect, filename=str(image_path))
    document.save(str(pdf_path))
    document.close()
    return pdf_path


def test_compress_reduces_image_pdf(workspace):
    source = _image_pdf(workspace)
    original_size = source.stat().st_size

    result = compress_pdf(source, workspace, level="Maximum compression")

    output = result.outputs[0]
    assert output.exists()
    assert output.stat().st_size < original_size
    assert "smaller" in result.note
    assert source.stat().st_size == original_size  # original untouched


def test_compress_never_grows_the_file(sample_pdf, workspace):
    original_size = sample_pdf.stat().st_size

    result = compress_pdf(sample_pdf, workspace, level="Low compression")

    assert result.outputs[0].stat().st_size <= original_size


def test_compress_output_is_still_readable(workspace):
    source = _image_pdf(workspace)

    output = compress_pdf(source, workspace, level="Balanced").outputs[0]

    with fitz.open(output) as document:
        assert document.page_count == 1


def test_compress_rejects_unknown_level(sample_pdf, workspace):
    with pytest.raises(ValueError, match="compression level"):
        compress_pdf(sample_pdf, workspace, level="tiny")


def test_compress_leaves_no_temporary_folders(sample_pdf, workspace):
    compress_pdf(sample_pdf, workspace, level="Balanced")

    assert not list(workspace.glob(".compress_*"))


def test_repair_rebuilds_a_valid_pdf(sample_pdf, workspace):
    result = repair_pdf(sample_pdf, workspace)

    output = result.outputs[0]
    assert output.read_bytes().startswith(b"%PDF")
    with fitz.open(output) as document:
        assert document.page_count == 3


def test_repair_recovers_a_pdf_with_a_broken_trailer(sample_pdf, workspace):
    damaged = workspace / "damaged.pdf"
    data = sample_pdf.read_bytes()
    damaged.write_bytes(data[: data.rfind(b"startxref")] + b"startxref\n999999\n%%EOF\n")

    result = repair_pdf(damaged, workspace)

    with fitz.open(result.outputs[0]) as document:
        assert document.page_count == 3


def test_repair_rejects_a_file_that_is_not_a_pdf(workspace):
    broken = workspace / "not_a_pdf.pdf"
    broken.write_bytes(b"this is plain text, not a PDF at all")

    with pytest.raises(ValueError, match="too damaged|could not be read"):
        repair_pdf(broken, workspace)
