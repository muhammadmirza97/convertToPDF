"""Compare two PDF versions locally: a text difference report and a visual diff PDF."""

from __future__ import annotations

import difflib
from pathlib import Path

import fitz

from .choices import match_choice
from .output_paths import safe_output_path
from .pdf_tools import open_document
from .tool_result import ToolOutput


COMPARE_MODES = ("Text and visual", "Text only", "Visual only")


def _page_lines(document: fitz.Document) -> list[list[str]]:
    return [
        [line for line in document.load_page(index).get_text().splitlines() if line.strip()]
        for index in range(document.page_count)
    ]


def _text_report(
    first_name: str,
    second_name: str,
    first_pages: list[list[str]],
    second_pages: list[list[str]],
) -> tuple[str, int]:
    lines: list[str] = [
        f"# Comparison report",
        "",
        f"- Old file: {first_name} ({len(first_pages)} page(s))",
        f"- New file: {second_name} ({len(second_pages)} page(s))",
        "",
    ]
    changed_pages = 0

    if len(first_pages) != len(second_pages):
        lines.append(
            f"Page count changed: {len(first_pages)} to {len(second_pages)}."
        )
        lines.append("")

    for index in range(max(len(first_pages), len(second_pages))):
        old = first_pages[index] if index < len(first_pages) else []
        new = second_pages[index] if index < len(second_pages) else []
        if old == new:
            continue
        changed_pages += 1
        lines.append(f"## Page {index + 1}")
        lines.append("")
        if not old:
            lines.append("Page only exists in the new file.")
        elif not new:
            lines.append("Page only exists in the old file.")
        else:
            lines.append("```diff")
            for row in difflib.unified_diff(old, new, lineterm="", n=1):
                if row.startswith(("---", "+++", "@@")):
                    continue
                lines.append(row)
            lines.append("```")
        lines.append("")

    if changed_pages == 0:
        lines.append("No text differences were found.")
        lines.append("")
    else:
        lines.insert(4, f"- Pages with text changes: {changed_pages}")

    return "\n".join(lines).strip() + "\n", changed_pages


def _visual_diff(
    first: fitz.Document,
    second: fitz.Document,
    output_path: Path,
    dpi: int,
) -> int:
    """Write a PDF where each page shows old, new, and the changed pixels in red."""
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    report = fitz.open()
    changed = 0

    for index in range(max(first.page_count, second.page_count)):
        old_pixmap = (
            first.load_page(index).get_pixmap(matrix=matrix, alpha=False)
            if index < first.page_count
            else None
        )
        new_pixmap = (
            second.load_page(index).get_pixmap(matrix=matrix, alpha=False)
            if index < second.page_count
            else None
        )
        reference = old_pixmap or new_pixmap
        if reference is None:
            continue

        width, height = reference.width, reference.height
        page = report.new_page(width=width * 0.75, height=height * 0.5 + 24)
        half = page.rect.width / 2

        page.insert_text((8, 14), f"Page {index + 1} - old (left) and new (right)", fontsize=9)
        if old_pixmap:
            page.insert_image(fitz.Rect(4, 20, half - 2, page.rect.height - 4), pixmap=old_pixmap)
        if new_pixmap:
            page.insert_image(
                fitz.Rect(half + 2, 20, page.rect.width - 4, page.rect.height - 4),
                pixmap=new_pixmap,
            )

        if old_pixmap and new_pixmap and old_pixmap.samples != new_pixmap.samples:
            changed += 1
            page.draw_rect(
                fitz.Rect(half + 2, 20, page.rect.width - 4, page.rect.height - 4),
                color=(0.85, 0.1, 0.1),
                width=2,
            )
            page.insert_text(
                (half + 6, 14), "changed", fontsize=9, color=(0.85, 0.1, 0.1)
            )
        elif not (old_pixmap and new_pixmap):
            changed += 1

    if report.page_count == 0:
        report.close()
        raise ValueError("Neither PDF has any pages to compare.")
    report.save(str(output_path), garbage=3, deflate=True)
    report.close()
    return changed


def compare_pdfs(
    input_paths: list[str | Path],
    output_dir: str | Path,
    *,
    mode: str = "Text and visual",
    dpi: int = 100,
    password: str | None = None,
) -> ToolOutput:
    """Compare exactly two PDFs. The first file selected is treated as the older one."""
    if len(input_paths) != 2:
        raise ValueError("Compare needs exactly two PDF files: the old one, then the new one.")
    wanted = match_choice(mode, COMPARE_MODES, "a comparison mode")
    if not 40 <= int(dpi) <= 300:
        raise ValueError("Choose a comparison resolution between 40 and 300 DPI.")

    first_path, second_path = Path(input_paths[0]), Path(input_paths[1])
    outputs: list[Path] = []
    notes: list[str] = []

    first = open_document(first_path, password)
    second = open_document(second_path, password)
    try:
        if wanted in ("Text and visual", "Text only"):
            report, changed = _text_report(
                first_path.name, second_path.name, _page_lines(first), _page_lines(second)
            )
            text_path = safe_output_path(
                output_dir, f"{first_path.stem}_vs_{second_path.stem}", ".md"
            )
            text_path.write_text(report, encoding="utf-8")
            outputs.append(text_path)
            notes.append(
                "no text differences" if changed == 0 else f"{changed} page(s) differ in text"
            )

        if wanted in ("Text and visual", "Visual only"):
            visual_path = safe_output_path(
                output_dir, f"{first_path.stem}_vs_{second_path.stem}_visual", ".pdf"
            )
            changed = _visual_diff(first, second, visual_path, int(dpi))
            outputs.append(visual_path)
            notes.append(
                "no visual differences" if changed == 0 else f"{changed} page(s) look different"
            )
    finally:
        first.close()
        second.close()

    return ToolOutput(outputs, "; ".join(notes))
