from __future__ import annotations

import pikepdf
import pytest
from pypdf import PdfReader

from src.pdf_security import protect_pdf, read_metadata, strip_metadata, unlock_pdf
from src.pdf_tools import pdf_to_text


def test_protect_produces_an_encrypted_copy(sample_pdf, workspace):
    output = protect_pdf(sample_pdf, workspace, new_password="secret123")

    assert PdfReader(str(output)).is_encrypted
    assert not PdfReader(str(sample_pdf)).is_encrypted  # original untouched


def test_protected_pdf_cannot_be_read_without_the_password(sample_pdf, workspace):
    output = protect_pdf(sample_pdf, workspace, new_password="secret123")

    with pytest.raises(ValueError, match="password protected"):
        pdf_to_text(output, workspace)


def test_protect_then_unlock_round_trip(sample_pdf, workspace):
    protected = protect_pdf(sample_pdf, workspace, new_password="secret123")

    unlocked = unlock_pdf(protected, workspace, password="secret123")

    assert not PdfReader(str(unlocked)).is_encrypted
    assert "Sample page 1" in pdf_to_text(unlocked, workspace).read_text(encoding="utf-8")


def test_protect_rejects_mismatched_confirmation(sample_pdf, workspace):
    with pytest.raises(ValueError, match="do not match"):
        protect_pdf(sample_pdf, workspace, new_password="secret123", confirm_password="secret124")


def test_protect_rejects_short_password(sample_pdf, workspace):
    with pytest.raises(ValueError, match="at least 4"):
        protect_pdf(sample_pdf, workspace, new_password="ab")


def test_protect_rejects_blank_password(sample_pdf, workspace):
    with pytest.raises(ValueError, match="Enter the password"):
        protect_pdf(sample_pdf, workspace, new_password="   ")


def test_protect_respects_copy_permission(sample_pdf, workspace):
    output = protect_pdf(sample_pdf, workspace, new_password="secret123", allow_copying=False)

    with pikepdf.open(output, password="secret123") as pdf:
        assert not pdf.allow.extract


def test_unlock_rejects_the_wrong_password(sample_pdf, workspace):
    protected = protect_pdf(sample_pdf, workspace, new_password="secret123")

    with pytest.raises(ValueError, match="not correct"):
        unlock_pdf(protected, workspace, password="wrong")


def test_unlock_needs_a_password(sample_pdf, workspace):
    with pytest.raises(ValueError, match="Enter the current password"):
        unlock_pdf(sample_pdf, workspace, password="")


def test_unlock_reports_unprotected_files(sample_pdf, workspace):
    with pytest.raises(ValueError, match="not password protected"):
        unlock_pdf(sample_pdf, workspace, password="anything")


def test_strip_metadata_removes_document_information(sample_pdf, workspace):
    assert read_metadata(sample_pdf)  # reportlab writes Producer/CreationDate

    result = strip_metadata(sample_pdf, workspace)

    assert not read_metadata(result.outputs[0])
    assert read_metadata(sample_pdf)  # original untouched


def test_strip_metadata_keeps_the_pages(sample_pdf, workspace):
    result = strip_metadata(sample_pdf, workspace)

    assert len(PdfReader(str(result.outputs[0])).pages) == 3
