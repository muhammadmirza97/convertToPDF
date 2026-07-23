"""Plain text to PDF conversion."""

from __future__ import annotations

import textwrap
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .output_paths import safe_output_path


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def txt_to_pdf(input_path: str | Path, output_dir: str | Path) -> Path:
    source = Path(input_path)
    output_path = safe_output_path(output_dir, source.stem, ".pdf")
    text = _read_text(source)

    _page_width, page_height = letter
    margin = 54
    line_height = 14
    max_chars = 90
    y = page_height - margin

    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    pdf.setTitle(source.name)
    pdf.setFont("Helvetica", 11)

    for raw_line in text.splitlines() or [""]:
        wrapped = textwrap.wrap(
            raw_line,
            width=max_chars,
            replace_whitespace=False,
            drop_whitespace=False,
        ) or [""]
        for line in wrapped:
            if y < margin:
                pdf.showPage()
                pdf.setFont("Helvetica", 11)
                y = page_height - margin
            safe_line = line.encode("latin-1", errors="replace").decode("latin-1")
            pdf.drawString(margin, y, safe_line)
            y -= line_height

    pdf.save()
    return output_path
