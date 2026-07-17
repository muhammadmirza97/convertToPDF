from __future__ import annotations

from src.config import (
    ACTION_IMAGES_TO_SINGLE_PDF,
    ACTION_MERGE_PDFS,
    ACTION_OFFICE_TO_PDF,
    ACTION_TXT_TO_PDF,
)
from src.file_validation import detect_input_types, validate_action, validate_output_folder


def test_detect_input_types(workspace):
    image = workspace / "photo.jpg"
    pdf = workspace / "doc.pdf"
    text = workspace / "notes.txt"
    for path in (image, pdf, text):
        path.write_text("sample", encoding="utf-8")

    assert detect_input_types([image, pdf, text]) == {"image", "pdf", "text"}


def test_merge_requires_two_pdfs(workspace):
    pdf = workspace / "one.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% sample\n")

    result = validate_action([pdf], workspace, ACTION_MERGE_PDFS)

    assert not result.ok
    assert "at least two" in result.message


def test_images_action_rejects_text_file(workspace):
    text = workspace / "notes.txt"
    text.write_text("hello", encoding="utf-8")

    result = validate_action([text], workspace, ACTION_IMAGES_TO_SINGLE_PDF)

    assert not result.ok
    assert "PNG/JPG/JPEG" in result.message


def test_office_conversion_requires_libreoffice(workspace):
    docx = workspace / "example.docx"
    docx.write_bytes(b"not a real docx")

    result = validate_action([docx], workspace, ACTION_OFFICE_TO_PDF, libreoffice_available=False)

    assert not result.ok
    assert "LibreOffice" in result.message


def test_unsupported_file_type_is_rejected(workspace):
    source = workspace / "archive.zip"
    source.write_bytes(b"not supported")

    result = validate_action([source], workspace, ACTION_IMAGES_TO_SINGLE_PDF)

    assert not result.ok
    assert "Unsupported" in result.message


def test_output_folder_rejects_existing_file_path(workspace):
    not_a_folder = workspace / "already_a_file"
    not_a_folder.write_text("content", encoding="utf-8")

    result = validate_output_folder(not_a_folder)

    assert not result.ok
    assert "not writable" in result.message


def test_validate_output_folder_has_no_side_effects(workspace):
    source = workspace / "notes.txt"
    source.write_text("sample", encoding="utf-8")
    output = workspace / "typed" / "partial"

    result = validate_action([source], output, ACTION_TXT_TO_PDF)

    assert result.ok
    assert not (workspace / "typed").exists()
