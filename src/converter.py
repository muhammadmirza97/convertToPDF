"""High-level conversion orchestration used by the GUI and tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .config import (
    ACTION_AI_SUMMARIZER,
    ACTION_AUTO,
    ACTION_IMAGES_TO_SINGLE_PDF,
    ACTION_MERGE_PDFS,
    ACTION_OFFICE_TO_PDF,
    ACTION_PDF_TO_PNG,
    ACTION_PDF_TO_TEXT,
    ACTION_SPLIT_PDF,
    ACTION_TXT_TO_PDF,
    ACTION_COMPARE_PDF,
    ACTION_COMPRESS_PDF,
    ACTION_CROP_PDF,
    ACTION_EDIT_PDF,
    ACTION_HTML_TO_PDF,
    ACTION_OCR_PDF,
    ACTION_ORGANIZE_PDF,
    ACTION_PAGE_NUMBERS,
    ACTION_PDF_FORMS,
    ACTION_PDF_TO_EXCEL,
    ACTION_PDF_TO_JPG,
    ACTION_PDF_TO_MARKDOWN,
    ACTION_PDF_TO_PDFA,
    ACTION_PDF_TO_POWERPOINT,
    ACTION_PDF_TO_WORD,
    ACTION_PROTECT_PDF,
    ACTION_REDACT_PDF,
    ACTION_REPAIR_PDF,
    ACTION_ROTATE_PDF,
    ACTION_SIGN_PDF,
    ACTION_TRANSLATE,
    ACTION_UNLOCK_PDF,
    ACTION_WATERMARK_PDF,
    IMAGE_EXTENSIONS,
    OFFICE_EXTENSIONS,
    PDF_EXTENSIONS,
    TEXT_EXTENSIONS,
)
from .file_validation import validate_action
from .image_tools import image_to_pdf, images_to_single_pdf
from .logger import setup_logging
from . import office_tools, pdf_tools, text_tools
from .office_tools import convert_office_to_pdf, find_libreoffice
from .pdf_tools import merge_pdfs, pdf_to_png, pdf_to_text, split_pdf
from .text_tools import txt_to_pdf

ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str], None]


@dataclass
class ConversionResult:
    input_path: Path | None
    outputs: list[Path] = field(default_factory=list)
    success: bool = True
    message: str = ""


@dataclass
class ConversionSummary:
    results: list[ConversionResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for result in self.results if result.success)

    @property
    def failed(self) -> int:
        return sum(1 for result in self.results if not result.success)

    @property
    def ok(self) -> bool:
        return self.failed == 0


def _log(message: str, callback: LogCallback | None) -> None:
    if callback:
        callback(message)


def _progress(done: int, total: int, message: str, callback: ProgressCallback | None) -> None:
    if callback:
        callback(done, total, message)


def convert_files(
    files: list[str | Path],
    output_dir: str | Path,
    action: str,
    *,
    page_ranges: str | None = None,
    options: dict[str, object] | None = None,
    progress_callback: ProgressCallback | None = None,
    log_callback: LogCallback | None = None,
) -> ConversionSummary:
    """Convert files for the selected action and keep batch errors isolated."""
    logger = setup_logging()
    soffice = find_libreoffice()
    logger.info(
        "Starting conversion action=%s file_count=%s output_folder=%s libreoffice=%s",
        action,
        len(files),
        Path(output_dir).name or "selected folder",
        "detected" if soffice else "not detected",
    )
    validation = validate_action(files, output_dir, action, libreoffice_available=soffice is not None)
    if not validation.ok:
        logger.warning("Conversion validation failed: %s", validation.message)
        raise ValueError(validation.message)

    paths = validation.files
    summary = ConversionSummary()

    def record_success(input_path: Path | None, outputs: list[Path], message: str) -> None:
        logger.info("%s | output_count=%s output_names=%s", message, len(outputs), [path.name for path in outputs])
        _log(message, log_callback)
        summary.results.append(ConversionResult(input_path, outputs, True, message))

    def record_failure(input_path: Path | None, exc: Exception) -> None:
        label = input_path.name if input_path else "conversion"
        message = f"Failed: {label} - {exc}"
        if isinstance(exc, ValueError):
            logger.warning(message)
        else:
            logger.exception(message)
        _log(message, log_callback)
        summary.results.append(ConversionResult(input_path, [], False, message))

    options = dict(options or {})

    if action == ACTION_MERGE_PDFS:
        _progress(0, 1, "Merging PDFs...", progress_callback)
        try:
            output = merge_pdfs(paths, output_dir)
            record_success(None, [output], f"Merged {len(paths)} PDFs into {output.name}.")
        except Exception as exc:
            record_failure(None, exc)
        _progress(1, 1, "Done.", progress_callback)
        return summary

    if action == ACTION_COMPARE_PDF:
        _progress(0, 1, "Comparing PDFs...", progress_callback)
        try:
            output = pdf_tools.compare_pdfs(paths[0], paths[1], output_dir)
            record_success(None, [output], f"Comparison report saved as {output.name}.")
        except Exception as exc:
            record_failure(None, exc)
        _progress(1, 1, "Done.", progress_callback)
        return summary

    if action == ACTION_ORGANIZE_PDF:
        _progress(0, 1, "Organizing PDF...", progress_callback)
        try:
            order = options.pop("page_order", None)
            output = pdf_tools.organize_pdf(paths[0], output_dir, page_order=order, **options)
            record_success(paths[0], [output], f"Organized {paths[0].name}.")
        except Exception as exc:
            record_failure(paths[0], exc)
        _progress(1, 1, "Done.", progress_callback)
        return summary

    if action == ACTION_IMAGES_TO_SINGLE_PDF:
        _progress(0, 1, "Combining images...", progress_callback)
        try:
            output = images_to_single_pdf(paths, output_dir)
            record_success(None, [output], f"Combined {len(paths)} images into {output.name}.")
        except Exception as exc:
            record_failure(None, exc)
        _progress(1, 1, "Done.", progress_callback)
        return summary

    total = len(paths)
    for index, path in enumerate(paths, start=1):
        _progress(index - 1, total, f"Working on {path.name}...", progress_callback)
        try:
            outputs = _convert_single(path, output_dir, action, page_ranges=page_ranges, soffice=soffice, options=options)
            record_success(path, outputs, f"Converted {path.name}.")
        except Exception as exc:
            record_failure(path, exc)
        _progress(index, total, f"Finished {path.name}.", progress_callback)

    return summary


def _convert_single(
    path: Path,
    output_dir: str | Path,
    action: str,
    *,
    page_ranges: str | None,
    soffice: Path | None,
    options: dict[str, object] | None = None,
) -> list[Path]:
    ext = path.suffix.lower()
    kwargs = dict(options or {})

    if action == ACTION_AUTO:
        if ext in IMAGE_EXTENSIONS:
            return [image_to_pdf(path, output_dir)]
        if ext in TEXT_EXTENSIONS:
            return [txt_to_pdf(path, output_dir)]
        if ext in OFFICE_EXTENSIONS:
            return [convert_office_to_pdf(path, output_dir, soffice_path=soffice)]
        if ext in PDF_EXTENSIONS:
            raise ValueError("PDF input has no automatic PDF conversion. Choose a PDF action.")
        raise ValueError(f"Unsupported file type: {ext}")

    if action == ACTION_PDF_TO_PNG:
        return pdf_to_png(path, output_dir)
    if action == ACTION_PDF_TO_TEXT:
        return [pdf_to_text(path, output_dir)]
    if action == ACTION_SPLIT_PDF:
        return split_pdf(path, output_dir, page_ranges=page_ranges)
    if action == ACTION_TXT_TO_PDF:
        return [txt_to_pdf(path, output_dir)]
    if action == ACTION_OFFICE_TO_PDF:
        return [convert_office_to_pdf(path, output_dir, soffice_path=soffice)]
    if action == ACTION_PDF_TO_JPG:
        return pdf_tools.pdf_to_images(path, output_dir, image_format="jpg", **kwargs)
    if action == ACTION_COMPRESS_PDF:
        return [pdf_tools.compress_pdf(path, output_dir, **kwargs)]
    if action == ACTION_REPAIR_PDF:
        return [pdf_tools.repair_pdf(path, output_dir)]
    if action == ACTION_OCR_PDF:
        return [pdf_tools.ocr_pdf(path, output_dir, **kwargs)]
    if action == ACTION_PDF_TO_WORD:
        return [office_tools.pdf_to_word(path, output_dir)]
    if action == ACTION_PDF_TO_POWERPOINT:
        return [office_tools.pdf_to_powerpoint(path, output_dir)]
    if action == ACTION_PDF_TO_EXCEL:
        return [office_tools.pdf_to_excel(path, output_dir)]
    if action == ACTION_HTML_TO_PDF:
        return [pdf_tools.html_to_pdf(path, output_dir)]
    if action == ACTION_PDF_TO_PDFA:
        return [office_tools.convert_pdf_to_pdfa(path, output_dir, soffice_path=soffice)]
    if action == ACTION_EDIT_PDF:
        return [pdf_tools.edit_pdf(path, output_dir, **kwargs)]
    if action == ACTION_WATERMARK_PDF:
        return [pdf_tools.watermark_pdf(path, output_dir, **kwargs)]
    if action == ACTION_ROTATE_PDF:
        return [pdf_tools.rotate_pdf(path, output_dir, page_ranges=page_ranges, **kwargs)]
    if action == ACTION_PAGE_NUMBERS:
        return [pdf_tools.add_page_numbers(path, output_dir, **kwargs)]
    if action == ACTION_CROP_PDF:
        return [pdf_tools.crop_pdf(path, output_dir, **kwargs)]
    if action == ACTION_PDF_FORMS:
        if "field_name" in kwargs:
            return [pdf_tools.create_pdf_form(path, output_dir, **kwargs)]
        return [pdf_tools.fill_pdf_form(path, output_dir, **kwargs)]
    if action == ACTION_SIGN_PDF:
        return [pdf_tools.sign_pdf(path, output_dir, **kwargs)]
    if action == ACTION_UNLOCK_PDF:
        return [pdf_tools.unlock_pdf(path, output_dir, **kwargs)]
    if action == ACTION_PROTECT_PDF:
        return [pdf_tools.protect_pdf(path, output_dir, **kwargs)]
    if action == ACTION_REDACT_PDF:
        return [pdf_tools.redact_pdf(path, output_dir, **kwargs)]
    if action == ACTION_PDF_TO_MARKDOWN:
        return [text_tools.pdf_to_markdown(path, output_dir)]
    if action == ACTION_AI_SUMMARIZER:
        return [text_tools.local_ai_process(path, output_dir, task="summarize", **kwargs)]
    if action == ACTION_TRANSLATE:
        return [text_tools.local_ai_process(path, output_dir, task="translate", **kwargs)]

    raise ValueError(f"Unsupported action: {action}")
