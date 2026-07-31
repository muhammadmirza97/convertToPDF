"""Input and output validation, driven by the tool registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import (
    HTML_EXTENSIONS,
    IMAGE_EXTENSIONS,
    OFFICE_EXTENSIONS,
    PDF_EXTENSIONS,
    REQUIRES_LIBREOFFICE,
    REQUIRES_TESSERACT,
    SUPPORTED_INPUT_EXTENSIONS,
    TEXT_EXTENSIONS,
)
from .output_paths import is_writable_directory
from .tool_registry import Tool, find_tool


DEPENDENCY_MESSAGES = {
    REQUIRES_LIBREOFFICE: "LibreOffice was not found, so Office conversion is unavailable.",
    REQUIRES_TESSERACT: "Tesseract OCR was not found, so OCR is unavailable.",
}

DEPENDENCY_LABELS = {
    REQUIRES_LIBREOFFICE: "LibreOffice",
    REQUIRES_TESSERACT: "Tesseract OCR",
}


def missing_dependencies() -> set[str]:
    """Report which optional local engines are absent right now."""
    from .ocr_tools import find_tessdata, find_tesseract
    from .office_tools import find_libreoffice

    missing: set[str] = set()
    if find_libreoffice() is None:
        missing.add(REQUIRES_LIBREOFFICE)
    if find_tesseract() is None or find_tessdata() is None:
        missing.add(REQUIRES_TESSERACT)
    return missing


@dataclass
class ValidationResult:
    ok: bool
    message: str
    files: list[Path] = field(default_factory=list)


def extension_for(path: str | Path) -> str:
    return Path(path).suffix.lower()


def detect_input_types(files: list[str | Path]) -> set[str]:
    groups = {
        "image": IMAGE_EXTENSIONS,
        "pdf": PDF_EXTENSIONS,
        "text": TEXT_EXTENSIONS,
        "html": HTML_EXTENSIONS,
        "office": OFFICE_EXTENSIONS,
    }
    types: set[str] = set()
    for item in files:
        ext = extension_for(item)
        name = next((label for label, exts in groups.items() if ext in exts), "unsupported")
        types.add(name)
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


def validate_tool(
    tool: Tool | None,
    files: list[str | Path],
    output_folder: str | Path | None,
    *,
    missing_dependencies: set[str] | None = None,
) -> ValidationResult:
    """Check files, output folder and dependencies for one tool."""
    if tool is None:
        return ValidationResult(False, "Choose a tool.")

    file_result = validate_files(files)
    if not file_result.ok:
        return file_result

    folder_result = validate_output_folder(output_folder)
    if not folder_result.ok:
        return ValidationResult(folder_result.ok, folder_result.message, file_result.files)

    rejection = tool.rejects(file_result.files)
    if rejection:
        return ValidationResult(False, rejection, file_result.files)

    needed = tool.resolve_requires(file_result.files)
    if needed and needed in (missing_dependencies or set()):
        message = tool.dependency_message or DEPENDENCY_MESSAGES.get(
            needed, f"{needed} is required but was not found."
        )
        return ValidationResult(False, message, file_result.files)

    return ValidationResult(True, "Ready to convert.", file_result.files)


def validate_tool_id(
    tool_id: str | None,
    files: list[str | Path],
    output_folder: str | Path | None,
    *,
    missing: set[str] | None = None,
) -> ValidationResult:
    """Validate by tool id or label, for callers that hold a name rather than a Tool."""
    if not tool_id:
        return ValidationResult(False, "Choose a tool.", validate_files(files).files)

    tool = find_tool(tool_id)
    if tool is None:
        return ValidationResult(False, "Choose a valid tool.", validate_files(files).files)

    return validate_tool(tool, files, output_folder, missing_dependencies=missing)
