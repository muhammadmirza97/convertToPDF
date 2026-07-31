"""Tool orchestration used by the GUI, the CLI and tests."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .config import (
    HTML_EXTENSIONS,
    IMAGE_EXTENSIONS,
    OFFICE_EXTENSIONS,
    PDF_EXTENSIONS,
    REQUIRES_LIBREOFFICE,
    TEXT_EXTENSIONS,
)
from .file_validation import missing_dependencies, validate_tool
from .html_tools import html_to_pdf
from .image_tools import image_to_pdf
from .logger import setup_logging
from .office_tools import convert_office_to_pdf, find_libreoffice
from .text_tools import txt_to_pdf
from .tool_registry import Tool, get_tool
from .tool_result import ToolOutput

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

    @property
    def outputs(self) -> list[Path]:
        return [output for result in self.results for output in result.outputs]


def _log(message: str, callback: LogCallback | None) -> None:
    if callback:
        callback(message)


def _progress(done: int, total: int, message: str, callback: ProgressCallback | None) -> None:
    if callback:
        callback(done, total, message)


def auto_convert_one(path: Path, output_dir: Path, **options: Any) -> Path:
    """Convert one non-PDF file to PDF based on its extension."""
    ext = path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return image_to_pdf(path, output_dir)
    if ext in TEXT_EXTENSIONS:
        return txt_to_pdf(path, output_dir)
    if ext in HTML_EXTENSIONS:
        return html_to_pdf(path, output_dir)
    if ext in OFFICE_EXTENSIONS:
        return convert_office_to_pdf(path, output_dir, soffice_path=options.get("soffice_path"))
    if ext in PDF_EXTENSIONS:
        raise ValueError("PDF input has no automatic PDF conversion. Choose a PDF action.")
    raise ValueError(f"Unsupported file type: {ext}")


def _normalize(result: Any) -> tuple[list[Path], str]:
    if isinstance(result, ToolOutput):
        return list(result.outputs), result.note
    if isinstance(result, Path):
        return [result], ""
    if isinstance(result, (list, tuple)):
        return [Path(item) for item in result], ""
    if result is None:
        return [], ""
    return [Path(result)], ""


def _accepts_soffice(processor: Callable[..., Any]) -> bool:
    try:
        signature = inspect.signature(processor)
    except (TypeError, ValueError):
        return False
    if "soffice_path" in signature.parameters:
        return True
    return any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def run_tool(
    tool: Tool | str,
    files: list[str | Path],
    output_dir: str | Path,
    options: dict[str, Any] | None = None,
    *,
    progress_callback: ProgressCallback | None = None,
    log_callback: LogCallback | None = None,
) -> ConversionSummary:
    """Run one registered tool over the chosen files, isolating per-file failures."""
    resolved = tool if isinstance(tool, Tool) else get_tool(tool)
    logger = setup_logging()
    soffice = find_libreoffice()
    missing = missing_dependencies()
    if soffice is None:
        missing.add(REQUIRES_LIBREOFFICE)
    else:
        missing.discard(REQUIRES_LIBREOFFICE)

    logger.info(
        "Starting tool=%s file_count=%s output_folder=%s libreoffice=%s",
        resolved.id,
        len(files),
        Path(output_dir).name or "selected folder",
        "detected" if soffice else "not detected",
    )

    validation = validate_tool(resolved, files, output_dir, missing_dependencies=missing)
    if not validation.ok:
        logger.warning("Validation failed for %s: %s", resolved.id, validation.message)
        raise ValueError(validation.message)

    values = resolved.coerce_options(options)
    if _accepts_soffice(resolved.processor):
        values["soffice_path"] = soffice

    paths = validation.files
    summary = ConversionSummary()

    def record_success(input_path: Path | None, outputs: list[Path], note: str) -> None:
        label = input_path.name if input_path else f"{len(paths)} file(s)"
        message = f"{resolved.label}: {label}"
        if note:
            message = f"{message} - {note}"
        if outputs:
            message = f"{message} -> {', '.join(output.name for output in outputs)}"
        logger.info("%s | output_count=%s", message, len(outputs))
        _log(message, log_callback)
        summary.results.append(ConversionResult(input_path, outputs, True, message))

    def record_failure(input_path: Path | None, exc: Exception) -> None:
        label = input_path.name if input_path else resolved.label
        message = f"Failed: {label} - {exc}"
        if isinstance(exc, ValueError):
            logger.warning(message)
        else:
            logger.exception(message)
        _log(message, log_callback)
        summary.results.append(ConversionResult(input_path, [], False, message))

    if not resolved.batch:
        _progress(0, 1, f"Running {resolved.label}...", progress_callback)
        try:
            outputs, note = _normalize(resolved.processor(list(paths), output_dir, **values))
            record_success(None, outputs, note)
        except Exception as exc:
            record_failure(None, exc)
        _progress(1, 1, "Done.", progress_callback)
        return summary

    total = len(paths)
    for index, path in enumerate(paths, start=1):
        _progress(index - 1, total, f"Working on {path.name}...", progress_callback)
        try:
            outputs, note = _normalize(resolved.processor(path, output_dir, **values))
            record_success(path, outputs, note)
        except Exception as exc:
            record_failure(path, exc)
        _progress(index, total, f"Finished {path.name}.", progress_callback)

    return summary


