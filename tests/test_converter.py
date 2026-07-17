from __future__ import annotations

import pytest
from PIL import Image

from src.config import ACTION_AUTO, ACTION_OFFICE_TO_PDF, ACTION_TXT_TO_PDF
from src.converter import convert_files


def test_auto_converts_image_and_text_without_crashing_batch(workspace):
    image_path = workspace / "picture.png"
    Image.new("RGB", (50, 40), "white").save(image_path)
    text_path = workspace / "notes.txt"
    text_path.write_text("hello from local converter", encoding="utf-8")

    summary = convert_files([image_path, text_path], workspace, ACTION_AUTO)

    assert summary.ok
    assert summary.succeeded == 2
    assert all(result.outputs for result in summary.results)


def test_txt_to_pdf_action(workspace):
    text_path = workspace / "notes.txt"
    text_path.write_text("plain text", encoding="utf-8")

    summary = convert_files([text_path], workspace, ACTION_TXT_TO_PDF)

    assert summary.ok
    assert summary.results[0].outputs[0].suffix == ".pdf"


def test_office_to_pdf_without_libreoffice_is_friendly(monkeypatch, workspace):
    monkeypatch.setattr("src.converter.find_libreoffice", lambda: None)
    docx = workspace / "letter.docx"
    docx.write_bytes(b"not a real docx")

    with pytest.raises(ValueError, match="LibreOffice"):
        convert_files([docx], workspace, ACTION_OFFICE_TO_PDF)


def test_batch_auto_reports_partial_failure_for_pdf_input(workspace):
    text_path = workspace / "notes.txt"
    text_path.write_text("plain text", encoding="utf-8")
    pdf_path = workspace / "already.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% invalid but extension is enough for validation\n")

    summary = convert_files([text_path, pdf_path], workspace, ACTION_AUTO)

    assert summary.succeeded == 1
    assert summary.failed == 1
    assert "Choose a PDF action" in summary.results[1].message
