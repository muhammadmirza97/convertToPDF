from __future__ import annotations

import fitz
import pytest
from pypdf import PdfReader

from src.pdf_edit import add_page_numbers, crop_pdf, watermark_pdf
from tests.conftest import build_image


def _page_text(path, page_index=0) -> str:
    with fitz.open(path) as document:
        return document.load_page(page_index).get_text()


def test_text_watermark_is_written_to_every_page(sample_pdf, workspace):
    output = watermark_pdf(sample_pdf, workspace, text="CONFIDENTIAL")

    with fitz.open(output) as document:
        assert document.page_count == 3
        assert all("CONFIDENTIAL" in page.get_text() for page in document)
    assert "CONFIDENTIAL" not in _page_text(sample_pdf)  # original untouched


def test_text_watermark_honours_page_selection(sample_pdf, workspace):
    output = watermark_pdf(sample_pdf, workspace, text="DRAFT", pages="2")

    assert "DRAFT" not in _page_text(output, 0)
    assert "DRAFT" in _page_text(output, 1)


def test_image_watermark(sample_pdf, workspace):
    stamp = build_image(workspace / "stamp.png", "red", (200, 100))

    output = watermark_pdf(sample_pdf, workspace, image_file=stamp, opacity=0.4)

    with fitz.open(output) as document:
        assert document.load_page(0).get_images()


def test_watermark_requires_text_or_image(sample_pdf, workspace):
    with pytest.raises(ValueError, match="not both"):
        watermark_pdf(sample_pdf, workspace)


def test_watermark_rejects_both_text_and_image(sample_pdf, workspace):
    stamp = build_image(workspace / "stamp.png")

    with pytest.raises(ValueError, match="not both"):
        watermark_pdf(sample_pdf, workspace, text="X", image_file=stamp)


def test_watermark_rejects_bad_opacity(sample_pdf, workspace):
    with pytest.raises(ValueError, match="opacity"):
        watermark_pdf(sample_pdf, workspace, text="X", opacity=5)


def test_watermark_rejects_missing_image(sample_pdf, workspace):
    with pytest.raises(ValueError, match="not found"):
        watermark_pdf(sample_pdf, workspace, image_file=workspace / "nope.png")


def test_page_numbers_use_the_chosen_format_and_start(sample_pdf, workspace):
    output = add_page_numbers(sample_pdf, workspace, number_format="Page 1", start_number=5)

    assert "Page 5" in _page_text(output, 0)
    assert "Page 7" in _page_text(output, 2)


def test_page_numbers_of_total_format(sample_pdf, workspace):
    output = add_page_numbers(sample_pdf, workspace, number_format="1 of 10")

    assert "1 of 3" in _page_text(output, 0)


def test_page_numbers_rejects_unknown_format(sample_pdf, workspace):
    with pytest.raises(ValueError, match="number format"):
        add_page_numbers(sample_pdf, workspace, number_format="roman")


def test_page_numbers_rejects_negative_start(sample_pdf, workspace):
    with pytest.raises(ValueError, match="negative"):
        add_page_numbers(sample_pdf, workspace, start_number=-2)


def test_crop_shrinks_the_crop_box(sample_pdf, workspace):
    before = PdfReader(str(sample_pdf)).pages[0].cropbox

    output = crop_pdf(sample_pdf, workspace, top_mm=10, bottom_mm=10, left_mm=5, right_mm=5)

    after = PdfReader(str(output)).pages[0].cropbox
    assert float(after.width) < float(before.width)
    assert float(after.height) < float(before.height)
    assert float(PdfReader(str(sample_pdf)).pages[0].cropbox.width) == float(before.width)


def test_crop_only_selected_pages(sample_pdf, workspace):
    output = crop_pdf(sample_pdf, workspace, top_mm=20, pages="1")

    pages = PdfReader(str(output)).pages
    assert float(pages[0].cropbox.height) < float(pages[1].cropbox.height)


def test_crop_requires_a_margin(sample_pdf, workspace):
    with pytest.raises(ValueError, match="at least one margin"):
        crop_pdf(sample_pdf, workspace)


def test_crop_rejects_margins_that_remove_everything(sample_pdf, workspace):
    with pytest.raises(ValueError, match="nothing visible"):
        crop_pdf(sample_pdf, workspace, top_mm=200, bottom_mm=200)


def test_crop_rejects_negative_margin(sample_pdf, workspace):
    with pytest.raises(ValueError, match="cannot be negative"):
        crop_pdf(sample_pdf, workspace, top_mm=-5)
