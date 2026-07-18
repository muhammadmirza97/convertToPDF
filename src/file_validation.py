"""Input and output validation for conversions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    ACTION_AUTO,
    ACTION_IMAGES_TO_SINGLE_PDF,
    ACTION_MERGE_PDFS,
    ACTION_OFFICE_TO_PDF,
    ACTION_PDF_TO_PNG,
    ACTION_PDF_TO_TEXT,
    ACTION_SPLIT_PDF,
    ACTION_TXT_TO_PDF,
    ACTIONS,
    HTML_EXTENSIONS,
    IMAGE_EXTENSIONS,
    OFFICE_EXTENSIONS,
    PDF_EXTENSIONS,
    SUPPORTED_INPUT_EXTENSIONS,
    TEXT_EXTENSIONS,
)
from .output_paths import is_writable_directory


@dataclass
class ValidationResult:
    ok: bool
    message: str
    files: list[Path] = field(default_factory=list)


def extension_for(path: str | Path) -> str:
    return Path(path).suffix.lower()


def detect_input_types(files: list[str | Path]) -> set[str]:
    types: set[str] = set()
    for item in files:
        ext = extension_for(item)
        if ext in IMAGE_EXTENSIONS:
            types.add("image")
        elif ext in PDF_EXTENSIONS:
            types.add("pdf")
        elif ext in TEXT_EXTENSIONS:
            types.add("text")
        elif ext in HTML_EXTENSIONS:
            types.add("html")
        elif ext in OFFICE_EXTENSIONS:
            types.add("office")
        else:
            types.add("unsupported")
    return types


def validate_files(files: list[str | Path]) -> ValidationResult:
    if not files:
        return ValidationResult(False, "Choose at least one file.")

    paths = [Path(file).expanduser() for file in files]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        return ValidationResult(False, f"File not found: {missing[0]}", paths)

    unsupported = [path.name for path in paths if path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS]
    if unsupported:
        return ValidationResult(False, f"Unsupported file type: {unsupported[0]}", paths)

    return ValidationResult(True, "Files look good.", paths)


def validate_output_folder(output_folder: str | Path | None) -> ValidationResult:
    if not output_folder:
        return ValidationResult(False, "Choose an output folder.")
    if not is_writable_directory(output_folder):
        return ValidationResult(False, "The output folder is not writable.")
    return ValidationResult(True, "Output folder is writable.")


def validate_action(
    files: list[str | Path],
    output_folder: str | Path | None,
    action: str | None,
    *,
    libreoffice_available: bool = False,
) -> ValidationResult:
    file_result = validate_files(files)
    if not file_result.ok:
        return file_result

    folder_result = validate_output_folder(output_folder)
    if not folder_result.ok:
        return folder_result

    if not action:
        return ValidationResult(False, "Choose a conversion action.", file_result.files)

    exts = [path.suffix.lower() for path in file_result.files]

    if action == ACTION_AUTO:
        if any(ext in OFFICE_EXTENSIONS for ext in exts) and not libreoffice_available:
            non_office = [ext for ext in exts if ext not in OFFICE_EXTENSIONS]
            if not non_office:
                return ValidationResult(
                    False,
                    "Office conversion needs LibreOffice. Other conversion tools still work.",
                    file_result.files,
                )
        return ValidationResult(True, "Ready to convert.", file_result.files)

    if action == ACTION_IMAGES_TO_SINGLE_PDF:
        if len(file_result.files) < 1 or any(ext not in IMAGE_EXTENSIONS for ext in exts):
            return ValidationResult(False, "Choose one or more PNG/JPG/JPEG images.", file_result.files)
    elif action == ACTION_PDF_TO_PNG:
        if any(ext not in PDF_EXTENSIONS for ext in exts):
            return ValidationResult(False, "PDF to PNG needs PDF input files.", file_result.files)
    elif action == ACTION_PDF_TO_TEXT:
        if any(ext not in PDF_EXTENSIONS for ext in exts):
            return ValidationResult(False, "PDF to text needs PDF input files.", file_result.files)
    elif action == ACTION_MERGE_PDFS:
        if len(file_result.files) < 2 or any(ext not in PDF_EXTENSIONS for ext in exts):
            return ValidationResult(False, "Merge needs at least two PDF files.", file_result.files)
    elif action == ACTION_SPLIT_PDF:
        if any(ext not in PDF_EXTENSIONS for ext in exts):
            return ValidationResult(False, "Split needs PDF input files.", file_result.files)
    elif action == ACTION_TXT_TO_PDF:
        if any(ext not in TEXT_EXTENSIONS for ext in exts):
            return ValidationResult(False, "TXT to PDF needs text files.", file_result.files)
    elif action == ACTION_OFFICE_TO_PDF:
        if any(ext not in OFFICE_EXTENSIONS for ext in exts):
            return ValidationResult(False, "Office to PDF needs DOC/DOCX/PPT/PPTX/XLS/XLSX files.", file_result.files)
        if not libreoffice_available:
            return ValidationResult(False, "LibreOffice was not found, so Office conversion is unavailable.", file_result.files)
    elif action == "Compare PDF":
        if len(file_result.files) != 2 or any(ext not in PDF_EXTENSIONS for ext in exts):
            return ValidationResult(False, "Compare needs exactly two PDF files.", file_result.files)
    elif action == "HTML to PDF":
        if any(ext not in HTML_EXTENSIONS for ext in exts):
            return ValidationResult(False, "HTML to PDF needs local HTML files.", file_result.files)
    elif action == "PDF to PDF/A":
        if any(ext not in PDF_EXTENSIONS for ext in exts):
            return ValidationResult(False, "PDF/A conversion needs PDF files.", file_result.files)
        if not libreoffice_available:
            return ValidationResult(False, "LibreOffice was not found, so PDF/A conversion is unavailable.", file_result.files)
    elif action in {"PDF to Word", "PDF to PowerPoint", "PDF to Excel", "PDF to JPG", "Organize PDF",
                    "Compress PDF", "Repair PDF", "OCR PDF", "Edit PDF", "Watermark PDF", "Rotate PDF",
                    "Page numbers", "Crop PDF", "PDF Forms", "Sign PDF", "Unlock PDF", "Protect PDF",
                    "Redact PDF", "PDF to Markdown", "AI Summarizer", "Translate"}:
        if any(ext not in PDF_EXTENSIONS for ext in exts):
            return ValidationResult(False, f"{action} needs PDF input files.", file_result.files)
        if action == "Organize PDF" and len(file_result.files) != 1:
            return ValidationResult(False, "Organize PDF needs one primary PDF.", file_result.files)
    elif action in ACTIONS:
        return ValidationResult(True, "Ready to convert.", file_result.files)
    else:
        return ValidationResult(False, "Choose a valid conversion action.", file_result.files)

    return ValidationResult(True, "Ready to convert.", file_result.files)
