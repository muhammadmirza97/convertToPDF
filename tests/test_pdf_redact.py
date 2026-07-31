from __future__ import annotations

import fitz
import pytest

from src.pdf_redact import parse_areas, redact_pdf
from tests.conftest import build_image


def _all_text(path) -> str:
    with fitz.open(path) as document:
        return "".join(page.get_text() for page in document)


def test_redacted_text_is_gone_from_the_file(invoice_pdf, workspace):
    result = redact_pdf(invoice_pdf, workspace, search_text="1234-5678")

    text = _all_text(result.outputs[0])
    assert "1234-5678" not in text
    assert "Invoice 1" in text                      # untouched content survives
    assert "1234-5678" in _all_text(invoice_pdf)    # original untouched


def test_redaction_can_write_a_replacement_label(invoice_pdf, workspace):
    result = redact_pdf(
        invoice_pdf, workspace, search_text="1234-5678", replacement_text="REDACTED"
    )

    assert "REDACTED" in _all_text(result.outputs[0])


def test_redaction_reports_how_many_areas_were_removed(invoice_pdf, workspace):
    result = redact_pdf(invoice_pdf, workspace, search_text="Account number")

    assert "Removed 2 area(s)" in result.note


def test_redaction_by_area(invoice_pdf, workspace):
    result = redact_pdf(invoice_pdf, workspace, areas="1:20,80,120,10")

    assert result.outputs[0].exists()


def test_redaction_removes_images_permanently(sample_pdf, workspace):
    logo = build_image(workspace / "logo.png", "teal", (200, 120))
    with fitz.open(sample_pdf) as document:
        page = document.load_page(0)
        page.insert_image(fitz.Rect(50, 50, 250, 170), filename=str(logo))
        with_image = workspace / "with_image.pdf"
        document.save(str(with_image))

    result = redact_pdf(with_image, workspace, remove_images=True, pages="1")

    with fitz.open(result.outputs[0]) as document:
        assert not document.load_page(0).get_images()


def test_redaction_needs_something_to_do(sample_pdf, workspace):
    with pytest.raises(ValueError, match="Enter text to redact"):
        redact_pdf(sample_pdf, workspace)


def test_redaction_reports_when_nothing_matched(invoice_pdf, workspace):
    with pytest.raises(ValueError, match="Nothing matched"):
        redact_pdf(invoice_pdf, workspace, search_text="not in this document")


def test_case_sensitive_redaction_can_miss_a_different_case(invoice_pdf, workspace):
    with pytest.raises(ValueError, match="Nothing matched"):
        redact_pdf(invoice_pdf, workspace, search_text="ACCOUNT NUMBER", case_sensitive=True)

    result = redact_pdf(invoice_pdf, workspace, search_text="ACCOUNT NUMBER", case_sensitive=False)
    assert result.outputs[0].exists()


def test_parse_areas_converts_millimetres_to_points():
    areas = parse_areas("2:10,20,30,40", page_count=3)

    left, top, right, bottom = areas[1][0]
    assert round(left, 1) == 28.3
    assert round(right - left, 1) == 85.0
    assert round(bottom - top, 1) == 113.4


def test_parse_areas_rejects_a_missing_page_number():
    with pytest.raises(ValueError, match="page number"):
        parse_areas("10,20,30,40", page_count=2)


def test_parse_areas_rejects_the_wrong_number_of_values():
    with pytest.raises(ValueError, match="four numbers"):
        parse_areas("1:10,20,30", page_count=2)


def test_parse_areas_rejects_a_page_out_of_range():
    with pytest.raises(ValueError, match="between 1 and 2"):
        parse_areas("9:10,20,30,40", page_count=2)


def test_parse_areas_ignores_blank_input():
    assert parse_areas("", page_count=2) == {}
