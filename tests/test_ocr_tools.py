"""OCR tests. Skipped automatically when Tesseract is not installed."""

from __future__ import annotations

import fitz
import pytest

from src.ocr_tools import available_languages, find_tessdata, find_tesseract, ocr_pdf
from tests.conftest import build_scanned_pdf

pytestmark = pytest.mark.skipif(
    find_tesseract() is None or find_tessdata() is None,
    reason="Tesseract OCR is not installed",
)


def test_english_language_pack_is_reported():
    assert "eng" in available_languages()


def test_ocr_makes_a_scanned_pdf_searchable(workspace):
    scan = build_scanned_pdf(workspace / "scan.pdf")
    with fitz.open(scan) as document:
        assert document.load_page(0).get_text().strip() == ""  # no text layer to begin with

    result = ocr_pdf(scan, workspace, dpi=200)

    with fitz.open(result.outputs[0]) as document:
        text = document.load_page(0).get_text().upper()
    assert "SCANNED" in text
    assert "HELLO" in text
    assert "OCR ran on 1 page(s)" in result.note


def test_ocr_keeps_the_page_image(workspace):
    scan = build_scanned_pdf(workspace / "scan.pdf")

    result = ocr_pdf(scan, workspace, dpi=150)

    with fitz.open(result.outputs[0]) as document:
        assert document.load_page(0).get_images()


def test_ocr_skips_pages_that_already_have_text(sample_pdf, workspace):
    with pytest.raises(ValueError, match="already has text"):
        ocr_pdf(sample_pdf, workspace, dpi=100)


def test_ocr_can_be_forced_on_pages_with_text(sample_pdf, workspace):
    result = ocr_pdf(sample_pdf, workspace, dpi=100, skip_pages_with_text=False, pages="1")

    assert "OCR ran on 1 page(s)" in result.note
    assert "2 page(s) kept" in result.note


def test_ocr_rejects_an_unavailable_language(workspace):
    scan = build_scanned_pdf(workspace / "scan.pdf")

    with pytest.raises(ValueError, match="not installed"):
        ocr_pdf(scan, workspace, language="zzz")


def test_ocr_rejects_a_silly_resolution(workspace):
    scan = build_scanned_pdf(workspace / "scan.pdf")

    with pytest.raises(ValueError, match="resolution"):
        ocr_pdf(scan, workspace, dpi=2000)


def test_ocr_leaves_the_original_untouched(workspace):
    scan = build_scanned_pdf(workspace / "scan.pdf")
    before = scan.read_bytes()

    ocr_pdf(scan, workspace, dpi=150)

    assert scan.read_bytes() == before
