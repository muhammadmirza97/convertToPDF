"""Tests for Sign PDF and Compare PDF."""

from __future__ import annotations

import fitz
import pytest

from src.pdf_compare import compare_pdfs
from src.pdf_sign import sign_pdf
from tests.conftest import build_pdf, build_signature_image


# --- signing ----------------------------------------------------------------


def test_signature_lands_on_the_last_page_by_default(sample_pdf, workspace):
    signature = build_signature_image(workspace / "sig.png")

    result = sign_pdf(sample_pdf, workspace, signature_image=signature)

    with fitz.open(result.outputs[0]) as document:
        assert not document.load_page(0).get_images()
        assert document.load_page(2).get_images()
    assert "Signed 1 page(s)" in result.note


def test_signature_can_target_chosen_pages(sample_pdf, workspace):
    signature = build_signature_image(workspace / "sig.png")

    result = sign_pdf(sample_pdf, workspace, signature_image=signature, pages="1-2")

    with fitz.open(result.outputs[0]) as document:
        assert document.load_page(0).get_images()
        assert document.load_page(1).get_images()


def test_signature_caption_is_written(sample_pdf, workspace):
    signature = build_signature_image(workspace / "sig.png")

    result = sign_pdf(
        sample_pdf, workspace, signature_image=signature, signed_by="Mirza", sign_date="2026-08-01"
    )

    with fitz.open(result.outputs[0]) as document:
        text = document.load_page(2).get_text()
    assert "Mirza" in text and "2026-08-01" in text


def test_signature_custom_position(sample_pdf, workspace):
    signature = build_signature_image(workspace / "sig.png")

    result = sign_pdf(
        sample_pdf,
        workspace,
        signature_image=signature,
        placement="Custom position",
        x_mm=30,
        y_mm=100,
    )

    assert result.outputs[0].exists()


def test_signature_note_is_honest_about_certification(sample_pdf, workspace):
    signature = build_signature_image(workspace / "sig.png")

    result = sign_pdf(sample_pdf, workspace, signature_image=signature)

    assert "not a certified digital signature" in result.note


def test_signing_needs_an_image(sample_pdf, workspace):
    with pytest.raises(ValueError, match="signature image"):
        sign_pdf(sample_pdf, workspace)


def test_signing_rejects_a_missing_image(sample_pdf, workspace):
    with pytest.raises(ValueError, match="not found"):
        sign_pdf(sample_pdf, workspace, signature_image=workspace / "ghost.png")


def test_signing_rejects_a_silly_width(sample_pdf, workspace):
    signature = build_signature_image(workspace / "sig.png")

    with pytest.raises(ValueError, match="width between"):
        sign_pdf(sample_pdf, workspace, signature_image=signature, width_mm=400)


# --- comparing --------------------------------------------------------------


def _changed_pdf(path, workspace):
    """A copy of the sample PDF with page 2 text changed."""
    changed = workspace / "changed.pdf"
    with fitz.open(path) as document:
        page = document.load_page(1)
        page.insert_text((72, 600), "extra line only in the new version", fontsize=11)
        document.save(str(changed))
    return changed


def test_compare_reports_text_differences(sample_pdf, workspace):
    changed = _changed_pdf(sample_pdf, workspace)

    result = compare_pdfs([sample_pdf, changed], workspace, mode="Text only", dpi=50)

    report = result.outputs[0].read_text(encoding="utf-8")
    assert result.outputs[0].suffix == ".md"
    assert "## Page 2" in report
    assert "extra line only in the new version" in report
    assert "differ in text" in result.note


def test_compare_says_so_when_files_match(sample_pdf, workspace):
    twin = workspace / "twin.pdf"
    twin.write_bytes(sample_pdf.read_bytes())

    result = compare_pdfs([sample_pdf, twin], workspace, mode="Text only")

    assert "No text differences" in result.outputs[0].read_text(encoding="utf-8")
    assert "no text differences" in result.note


def test_compare_writes_a_visual_report(sample_pdf, workspace):
    changed = _changed_pdf(sample_pdf, workspace)

    result = compare_pdfs([sample_pdf, changed], workspace, mode="Visual only", dpi=50)

    assert result.outputs[0].suffix == ".pdf"
    with fitz.open(result.outputs[0]) as document:
        assert document.page_count == 3


def test_compare_produces_both_reports(sample_pdf, workspace):
    changed = _changed_pdf(sample_pdf, workspace)

    result = compare_pdfs([sample_pdf, changed], workspace, dpi=50)

    assert [path.suffix for path in result.outputs] == [".md", ".pdf"]


def test_compare_notes_a_different_page_count(sample_pdf, workspace):
    shorter = build_pdf(workspace / "shorter.pdf", pages=1)

    result = compare_pdfs([sample_pdf, shorter], workspace, mode="Text only")

    assert "Page count changed: 3 to 1" in result.outputs[0].read_text(encoding="utf-8")


def test_compare_needs_exactly_two_files(sample_pdf, workspace):
    with pytest.raises(ValueError, match="exactly two"):
        compare_pdfs([sample_pdf], workspace)


def test_compare_rejects_a_silly_resolution(sample_pdf, workspace):
    twin = workspace / "twin.pdf"
    twin.write_bytes(sample_pdf.read_bytes())

    with pytest.raises(ValueError, match="resolution"):
        compare_pdfs([sample_pdf, twin], workspace, dpi=5000)
