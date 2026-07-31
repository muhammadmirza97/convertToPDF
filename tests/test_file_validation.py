from __future__ import annotations

from src.config import REQUIRES_LIBREOFFICE
from src.file_validation import (
    detect_input_types,
    validate_output_folder,
    validate_tool_id,
)


def test_detect_input_types(workspace):
    image = workspace / "photo.jpg"
    pdf = workspace / "doc.pdf"
    text = workspace / "notes.txt"
    page = workspace / "page.html"
    for path in (image, pdf, text, page):
        path.write_text("sample", encoding="utf-8")

    assert detect_input_types([image, pdf, text, page]) == {"image", "pdf", "text", "html"}


def test_merge_requires_two_pdfs(workspace):
    pdf = workspace / "one.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% sample\n")

    result = validate_tool_id("merge_pdfs", [pdf], workspace)

    assert not result.ok
    assert "at least two" in result.message


def test_images_tool_rejects_a_text_file(workspace):
    text = workspace / "notes.txt"
    text.write_text("hello", encoding="utf-8")

    result = validate_tool_id("images_to_pdf", [text], workspace)

    assert not result.ok
    assert "PNG/JPG/JPEG" in result.message


def test_office_conversion_requires_libreoffice(workspace):
    docx = workspace / "example.docx"
    docx.write_bytes(b"not a real docx")

    result = validate_tool_id(
        "office_to_pdf", [docx], workspace, missing={REQUIRES_LIBREOFFICE}
    )

    assert not result.ok
    assert "LibreOffice" in result.message


def test_ocr_requires_tesseract(workspace):
    from src.config import REQUIRES_TESSERACT

    pdf = workspace / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% sample\n")

    result = validate_tool_id("ocr_pdf", [pdf], workspace, missing={REQUIRES_TESSERACT})

    assert not result.ok
    assert "Tesseract" in result.message


def test_unsupported_file_type_is_rejected(workspace):
    source = workspace / "archive.zip"
    source.write_bytes(b"not supported")

    result = validate_tool_id("images_to_pdf", [source], workspace)

    assert not result.ok
    assert "Unsupported" in result.message


def test_unknown_tool_id_is_rejected(workspace):
    pdf = workspace / "one.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% sample\n")

    result = validate_tool_id("teleport_pdf", [pdf], workspace)

    assert not result.ok
    assert "valid tool" in result.message


def test_missing_tool_id_is_rejected(workspace):
    result = validate_tool_id("", [], workspace)

    assert not result.ok
    assert "Choose a tool" in result.message


def test_output_folder_rejects_existing_file_path(workspace):
    not_a_folder = workspace / "already_a_file"
    not_a_folder.write_text("content", encoding="utf-8")

    result = validate_output_folder(not_a_folder)

    assert not result.ok
    assert "not writable" in result.message
