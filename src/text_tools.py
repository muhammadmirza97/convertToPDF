"""Plain text to PDF conversion."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A3, A4, A5, LEGAL, LETTER, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import reportlab

from .choices import match_choice
from .output_paths import safe_output_path


MM_TO_POINTS = 72 / 25.4

PAGE_SIZES = {
    "A4": A4,
    "Letter": LETTER,
    "Legal": LEGAL,
    "A3": A3,
    "A5": A5,
}
ORIENTATIONS = ("Portrait", "Landscape")

_UNICODE_FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path(reportlab.__file__).parent / "fonts" / "Vera.ttf",
]
_FALLBACK_FONT = "Helvetica"
_registered_font: str | None = None


def unicode_font_name() -> str:
    """Register and return the widest-coverage font available locally."""
    global _registered_font
    if _registered_font:
        return _registered_font

    for candidate in _UNICODE_FONT_CANDIDATES:
        if not candidate.is_file():
            continue
        name = f"local_{candidate.stem}"
        try:
            pdfmetrics.registerFont(TTFont(name, str(candidate)))
        except Exception:
            continue
        _registered_font = name
        return name

    _registered_font = _FALLBACK_FONT
    return _FALLBACK_FONT


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _wrap(line: str, font: str, size: float, max_width: float) -> list[str]:
    if not line.strip():
        return [""]
    words = line.split(" ")
    rows: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if pdfmetrics.stringWidth(candidate, font, size) <= max_width or not current:
            current = candidate
            continue
        rows.append(current)
        current = word
    if current:
        rows.append(current)

    # Break any single word that is still too wide, character by character.
    final: list[str] = []
    for row in rows:
        while pdfmetrics.stringWidth(row, font, size) > max_width and len(row) > 1:
            cut = len(row) - 1
            while cut > 1 and pdfmetrics.stringWidth(row[:cut], font, size) > max_width:
                cut -= 1
            final.append(row[:cut])
            row = row[cut:]
        final.append(row)
    return final


def txt_to_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    font_size: int = 11,
    page_size: str = "Letter",
    orientation: str = "Portrait",
    margin_mm: float = 19.0,
) -> Path:
    size = int(font_size)
    if not 5 <= size <= 48:
        raise ValueError("Choose a font size between 5 and 48.")
    page = PAGE_SIZES[match_choice(page_size, PAGE_SIZES, "a page size")]
    wanted = match_choice(orientation, ORIENTATIONS, "an orientation")
    if wanted == "Landscape":
        page = landscape(page)
    if not 5 <= float(margin_mm) <= 60:
        raise ValueError("Choose a margin between 5 and 60 mm.")

    source = Path(input_path)
    output_path = safe_output_path(output_dir, source.stem, ".pdf")
    text = _read_text(source)

    font = unicode_font_name()
    page_width, page_height = page
    margin = float(margin_mm) * MM_TO_POINTS
    line_height = size * 1.3
    max_width = page_width - 2 * margin
    y = page_height - margin

    pdf = canvas.Canvas(str(output_path), pagesize=page)
    pdf.setTitle(source.name)
    pdf.setFont(font, size)

    for raw_line in text.splitlines() or [""]:
        for line in _wrap(raw_line.replace("\t", "    "), font, size, max_width):
            if y < margin:
                pdf.showPage()
                pdf.setFont(font, size)
                y = page_height - margin
            if font == _FALLBACK_FONT:
                line = line.encode("latin-1", errors="replace").decode("latin-1")
            pdf.drawString(margin, y, line)
            y -= line_height

    pdf.save()
    return output_path
