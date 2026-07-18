from __future__ import annotations

import io
import importlib.util

import fitz
import pytest
from PIL import Image
from pypdf import PdfReader

from src.pdf_tools import (
    add_page_numbers,
    compress_pdf,
    create_pdf_form,
    crop_pdf,
    fill_pdf_form,
    organize_pdf,
    protect_pdf,
    redact_pdf,
    rotate_pdf,
    unlock_pdf,
    watermark_pdf,
    compare_pdfs,
    edit_pdf,
    find_tesseract,
    html_to_pdf,
    ocr_pdf,
    pdf_to_images,
    repair_pdf,
    sign_pdf,
)
from src.office_tools import find_libreoffice, pdf_to_excel, pdf_to_powerpoint, pdf_to_word, convert_pdf_to_pdfa
from src.text_tools import local_ai_process, pdf_to_markdown


def _text_pdf(path, labels=("Alpha",), *, heading=False):
    document = fitz.open()
    for label in labels:
        page = document.new_page(width=612, height=792)
        page.insert_text((72, 100), label, fontsize=24 if heading else 12)
        if heading:
            page.insert_text((72, 145), "Body paragraph", fontsize=11)
    document.save(path)
    document.close()


def test_rotate_pdf(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source)
    output = rotate_pdf(source, tmp_path, degrees=90)
    assert PdfReader(output).pages[0].rotation == 90


def test_compress_size_decreases_for_image_pdf(tmp_path):
    source = tmp_path / "photo.pdf"
    image = Image.effect_noise((1600, 1600), 80).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    document = fitz.open()
    page = document.new_page(width=800, height=800)
    page.insert_image(page.rect, stream=buffer.getvalue())
    document.save(source)
    document.close()
    output = compress_pdf(source, tmp_path, preset="high")
    assert output.stat().st_size < source.stat().st_size


def test_protect_unlock_round_trip(tmp_path):
    source = tmp_path / "plain.pdf"
    _text_pdf(source, ("Private text",))
    protected = protect_pdf(source, tmp_path, password="correct horse")
    with fitz.open(protected) as encrypted:
        assert encrypted.needs_pass
        assert encrypted.authenticate("correct horse")
    unlocked = unlock_pdf(protected, tmp_path, password="correct horse")
    assert not PdfReader(unlocked).is_encrypted
    assert "Private text" in PdfReader(unlocked).pages[0].extract_text()


def test_watermark_and_page_numbers_are_extractable(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source, ("Page body",))
    marked = watermark_pdf(source, tmp_path, text="LOCAL MARK", opacity=0.5)
    numbered = add_page_numbers(marked, tmp_path, start_number=7, include_total=True)
    text = "".join(page.extract_text() or "" for page in PdfReader(numbered).pages)
    assert "LOCAL MARK" in text
    assert "7 of 7" in text


def test_cropbox_changed(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source)
    output = crop_pdf(source, tmp_path, rect=(36, 36, 500, 700))
    with fitz.open(output) as document:
        assert tuple(document[0].cropbox) == pytest.approx((36, 36, 500, 700))


def test_redacted_text_is_not_extractable(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source, ("Secret token 123",))
    output = redact_pdf(source, tmp_path, search_text="Secret token 123")
    with fitz.open(output) as document:
        assert "Secret token 123" not in "".join(page.get_text() for page in document)


def test_organize_page_order(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source, ("First", "Second", "Third"))
    output = organize_pdf(source, tmp_path, page_order=[2, 0])
    reader = PdfReader(output)
    assert len(reader.pages) == 2
    assert "Third" in reader.pages[0].extract_text()
    assert "First" in reader.pages[1].extract_text()


def test_form_fill_round_trip(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source)
    form = create_pdf_form(source, tmp_path, field_name="customer", rect=(72, 150, 260, 180))
    filled = fill_pdf_form(form, tmp_path, values={"customer": "Ada Lovelace"})
    fields = PdfReader(filled).get_fields()
    assert fields["customer"]["/V"] == "Ada Lovelace"


def test_markdown_heading(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source, ("Project Overview",), heading=True)
    output = pdf_to_markdown(source, tmp_path)
    assert output.read_text(encoding="utf-8").startswith("# Project Overview")


def test_jpg_html_repair_compare_edit_and_sign_smoke(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    _text_pdf(first, ("First version",))
    _text_pdf(second, ("Second version",))
    jpgs = pdf_to_images(first, tmp_path, image_format="jpg", dpi=72)
    assert jpgs[0].suffix == ".jpg"
    repaired = repair_pdf(first, tmp_path)
    assert repaired.exists()
    report = compare_pdfs(first, second, tmp_path)
    assert "First version" in report.read_text(encoding="utf-8")
    edited = edit_pdf(first, tmp_path, text="Added note", point=(72, 140))
    assert "Added note" in PdfReader(edited).pages[0].extract_text()
    signature = tmp_path / "signature.png"
    Image.new("RGB", (200, 60), "white").save(signature)
    signed = sign_pdf(first, tmp_path, signature_image=signature, rect=(72, 160, 220, 210))
    assert signed.exists()
    html = tmp_path / "local.html"
    html.write_text("<h1>Local HTML</h1><p>Offline content.</p>", encoding="utf-8")
    html_pdf = html_to_pdf(html, tmp_path)
    assert "Local HTML" in PdfReader(html_pdf).pages[0].extract_text()


def test_local_ai_is_off_by_default(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source)
    with pytest.raises(RuntimeError, match="Local AI not enabled"):
        local_ai_process(source, tmp_path, task="summarize")


@pytest.mark.skipif(find_tesseract() is None or importlib.util.find_spec("pytesseract") is None, reason="Tesseract/pytesseract not installed")
def test_ocr_optional_dependency(tmp_path):
    source = tmp_path / "scan.pdf"
    _text_pdf(source, ("OCR sample",))
    assert ocr_pdf(source, tmp_path).exists()


@pytest.mark.skipif(
    any(importlib.util.find_spec(name) is None for name in ("docx", "pptx", "openpyxl")),
    reason="Office export Python dependencies not installed",
)
def test_pdf_office_exports_optional_dependencies(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source)
    assert pdf_to_word(source, tmp_path).suffix == ".docx"
    assert pdf_to_powerpoint(source, tmp_path).suffix == ".pptx"
    assert pdf_to_excel(source, tmp_path).suffix == ".xlsx"


@pytest.mark.skipif(find_libreoffice() is None, reason="LibreOffice not installed")
def test_pdfa_optional_libreoffice(tmp_path):
    source = tmp_path / "source.pdf"
    _text_pdf(source)
    assert convert_pdf_to_pdfa(source, tmp_path).exists()
