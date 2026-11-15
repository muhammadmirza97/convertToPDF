"""LibreOffice conversions. Skipped automatically when LibreOffice is missing.

These call an external program, so the suite keeps them few and small.
"""

from __future__ import annotations

import pikepdf
import pytest

from src.office_tools import find_libreoffice, pdf_to_pdfa, pdf_to_word

pytestmark = pytest.mark.skipif(find_libreoffice() is None, reason="LibreOffice is not installed")


def test_pdf_to_word_keeps_the_text(sample_pdf, workspace):
    import zipfile

    output = pdf_to_word(sample_pdf, workspace)

    assert output.suffix == ".docx"
    with zipfile.ZipFile(output) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8", "replace")
    assert "Sample page 1" in document_xml
    assert "Sample page 3" in document_xml
    assert "%PDF-" not in document_xml


def test_pdf_to_pdfa_tags_the_file_as_archival(sample_pdf, workspace):
    output = pdf_to_pdfa(sample_pdf, workspace, version="PDF/A-1b")

    assert output.name == "sample_pdfa.pdf"
    with pikepdf.open(output) as pdf:
        metadata = pdf.open_metadata()
        assert metadata.get("pdfaid:part") == "1"
        assert metadata.get("pdfaid:conformance") == "B"


def test_pdf_to_pdfa_rejects_an_unknown_version(sample_pdf, workspace):
    with pytest.raises(ValueError, match="PDF/A version"):
        pdf_to_pdfa(sample_pdf, workspace, version="PDF/A-9z")
