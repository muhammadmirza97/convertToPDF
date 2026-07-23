"""Safe output path generation."""

from __future__ import annotations

import re
from pathlib import Path


WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def ensure_directory(path: str | Path) -> Path:
    output_dir = Path(path).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def is_writable_directory(path: str | Path) -> bool:
    try:
        output_dir = ensure_directory(path)
        probe = output_dir / ".write_test.tmp"
        with probe.open("w", encoding="utf-8") as handle:
            handle.write("ok")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def sanitize_base_name(base_name: str | Path) -> str:
    """Return a Windows-safe file stem for generated output names."""
    stem = Path(str(base_name)).stem.strip()
    stem = INVALID_FILENAME_CHARS.sub("_", stem)
    stem = re.sub(r"_+", "_", stem).strip(" ._")
    if not stem:
        stem = "converted"
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"{stem}_file"
    return stem[:120]


def _assert_inside_directory(path: Path, output_dir: Path) -> None:
    try:
        path.resolve().relative_to(output_dir.resolve())
    except ValueError as exc:
        raise ValueError("Generated output path escaped the selected output folder.") from exc


def safe_output_path(
    output_dir: str | Path,
    base_name: str,
    extension: str,
    *,
    start_index: int = 1,
) -> Path:
    """Return a non-existing output path, adding _001, _002, etc. when needed."""
    output = ensure_directory(output_dir)
    suffix = extension if extension.startswith(".") else f".{extension}"
    clean_base = sanitize_base_name(base_name)
    candidate = output / f"{clean_base}{suffix}"
    _assert_inside_directory(candidate, output)
    if not candidate.exists():
        return candidate

    index = start_index
    while True:
        candidate = output / f"{clean_base}_{index:03d}{suffix}"
        _assert_inside_directory(candidate, output)
        if not candidate.exists():
            return candidate
        index += 1


def derived_folder(output_dir: str | Path, base_name: str) -> Path:
    """Create a safe folder for multi-file outputs such as PDF page images."""
    output = ensure_directory(output_dir)
    clean_base = sanitize_base_name(base_name)
    candidate = output / clean_base
    _assert_inside_directory(candidate, output)
    if not candidate.exists():
        candidate.mkdir(parents=True)
        return candidate

    index = 1
    while True:
        candidate = output / f"{clean_base}_{index:03d}"
        _assert_inside_directory(candidate, output)
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
        index += 1
