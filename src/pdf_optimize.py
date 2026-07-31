"""PDF optimisation: compression and repair, using local engines only."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import fitz
import pikepdf

from .choices import match_choice
from .output_paths import ensure_directory, safe_output_path
from .pdf_tools import ENCRYPTED_MESSAGE, open_document
from .tool_result import ToolOutput, human_size


COMPRESSION_LEVELS = ("Low compression", "Balanced", "Maximum compression")

# level -> (dpi_threshold, dpi_target, jpeg_quality); None means images are left alone.
_LEVEL_SETTINGS: dict[str, tuple[int | None, int, int]] = {
    "low compression": (None, 0, 0),
    "balanced": (180, 150, 75),
    "maximum compression": (130, 96, 45),
}

_SAVE_OPTIONS = dict(
    garbage=4,
    deflate=True,
    deflate_images=True,
    deflate_fonts=True,
    clean=True,
    use_objstms=1,
)


_LEVEL_ALIASES = {
    "low": "Low compression",
    "lossless": "Low compression",
    "medium": "Balanced",
    "max": "Maximum compression",
    "maximum": "Maximum compression",
    "high": "Maximum compression",
}


def _normalize_level(level: str) -> str:
    key = (level or "").strip().lower()
    return match_choice(_LEVEL_ALIASES.get(key, level), COMPRESSION_LEVELS, "a compression level").lower()


def compress_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    level: str = "Balanced",
    password: str | None = None,
) -> ToolOutput:
    """Rewrite a PDF smaller. Never returns a file bigger than the original."""
    settings_key = _normalize_level(level)
    dpi_threshold, dpi_target, quality = _LEVEL_SETTINGS[settings_key]

    source = Path(input_path)
    original_size = source.stat().st_size
    output_root = ensure_directory(output_dir)

    with tempfile.TemporaryDirectory(prefix=".compress_", dir=output_root) as temp_dir:
        lossless = Path(temp_dir) / "lossless.pdf"
        document = open_document(source, password)
        try:
            document.save(str(lossless), **_SAVE_OPTIONS)
        finally:
            document.close()

        best = lossless
        if dpi_threshold is not None:
            lossy = Path(temp_dir) / "lossy.pdf"
            document = open_document(source, password)
            try:
                document.rewrite_images(
                    dpi_threshold=dpi_threshold,
                    dpi_target=dpi_target,
                    quality=quality,
                    lossy=True,
                    lossless=True,
                )
                document.save(str(lossy), **_SAVE_OPTIONS)
            finally:
                document.close()
            if lossy.exists() and lossy.stat().st_size < best.stat().st_size:
                best = lossy

        best_size = best.stat().st_size
        if best_size >= original_size:
            # Compression did not help; copy the original instead of growing the file.
            output_path = safe_output_path(output_root, f"{source.stem}_compressed", ".pdf")
            shutil.copyfile(source, output_path)
            return ToolOutput(
                [output_path],
                f"Already well compressed at {human_size(original_size)}; copied unchanged.",
            )

        output_path = safe_output_path(output_root, f"{source.stem}_compressed", ".pdf")
        shutil.move(str(best), str(output_path))

    saved = 100 - int(round(best_size / original_size * 100))
    note = f"{human_size(original_size)} to {human_size(best_size)} ({saved}% smaller)"
    return ToolOutput([output_path], note)


def repair_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    password: str | None = None,
) -> ToolOutput:
    """Rebuild a damaged PDF structure. Content that is already lost cannot return."""
    source = Path(input_path)
    output_root = ensure_directory(output_dir)
    output_path = safe_output_path(output_root, f"{source.stem}_repaired", ".pdf")
    errors: list[str] = []

    try:
        with pikepdf.open(source, password=password or "") as pdf:
            pdf.save(output_path, linearize=False)
        return ToolOutput([output_path], "Rebuilt with pikepdf.")
    except pikepdf.PasswordError:
        output_path.unlink(missing_ok=True)
        raise ValueError(ENCRYPTED_MESSAGE.format(name=source.name)) from None
    except Exception as exc:
        errors.append(f"pikepdf: {exc}")
        output_path.unlink(missing_ok=True)

    try:
        document = fitz.open(source)
    except Exception as exc:
        errors.append(f"PyMuPDF: {exc}")
        raise ValueError(
            f"{source.name} is too damaged to repair locally. Details: {'; '.join(errors)}"
        ) from exc

    try:
        if document.needs_pass and not (password and document.authenticate(password)):
            raise ValueError(ENCRYPTED_MESSAGE.format(name=source.name))
        if document.page_count < 1:
            raise ValueError(f"No readable pages were recovered from {source.name}.")
        output_path = safe_output_path(output_root, f"{source.stem}_repaired", ".pdf")
        document.save(str(output_path), garbage=4, clean=True, deflate=True)
        page_count = document.page_count
    finally:
        document.close()

    return ToolOutput([output_path], f"Rebuilt with PyMuPDF; recovered {page_count} page(s).")
