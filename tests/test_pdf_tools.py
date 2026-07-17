from __future__ import annotations

import pytest
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

from src.pdf_tools import merge_pdfs, parse_page_ranges, pdf_to_png, pdf_to_text, split_pdf


def _make_pdf(path, pages=1):
    pdf = canvas.Canvas(str(path))
    for page in range(1, pages + 1):
        pdf.drawString(72, 720, f"Sample page {page}")
        pdf.showPage()
    pdf.save()


def test_parse_page_ranges():
    assert parse_page_ranges("1-2,4", 5) == [(0, 1), (3, 3)]


def test_parse_page_ranges_rejects_non_numeric_text():
    with pytest.raises(ValueError, match="numbers"):
        parse_page_ranges("one-three", 5)


def test_merge_split_extract_and_render(workspace):
    first = workspace / "first.pdf"
    second = workspace / "second.pdf"
    _make_pdf(first, pages=2)
    _make_pdf(second, pages=1)

    merged = merge_pdfs([first, second], workspace)
    split_outputs = split_pdf(merged, workspace, page_ranges="1-2")
    text_output = pdf_to_text(merged, workspace)
    image_outputs = pdf_to_png(merged, workspace, dpi=72)

    assert merged.exists()
    assert len(split_outputs) == 1
    assert split_outputs[0].exists()
    assert "Sample page 1" in text_output.read_text(encoding="utf-8")
    assert len(image_outputs) == 3
    assert all(path.exists() and path.suffix == ".png" for path in image_outputs)


def test_encrypted_pdf_fails_gracefully(workspace):
    plain = workspace / "plain.pdf"
    encrypted = workspace / "encrypted.pdf"
    _make_pdf(plain, pages=1)
    reader = PdfReader(str(plain))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt("secret")
    with encrypted.open("wb") as handle:
        writer.write(handle)

    with pytest.raises(ValueError, match="Encrypted PDF"):
        pdf_to_text(encrypted, workspace)


def test_encrypted_pdf_text_does_not_create_output_dir(workspace):
    plain = workspace / "plain_side_effect.pdf"
    encrypted = workspace / "encrypted_side_effect.pdf"
    _make_pdf(plain, pages=1)
    reader = PdfReader(str(plain))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt("secret")
    with encrypted.open("wb") as handle:
        writer.write(handle)
    output = workspace / "fresh_out"

    with pytest.raises(ValueError, match="Encrypted PDF"):
        pdf_to_text(encrypted, output)

    assert not output.exists()
