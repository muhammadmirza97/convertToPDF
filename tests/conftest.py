from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from reportlab.pdfgen import canvas


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """An empty folder for one test's inputs and outputs.

    This is pytest's own temporary directory, so test runs never leave files inside the
    project folder. pytest keeps the last few runs under the system temp folder and clears
    older ones itself.
    """
    return tmp_path


def build_pdf(path: Path, pages: int = 3, *, heading: bool = False) -> Path:
    """Create a small text PDF for tests."""
    pdf = canvas.Canvas(str(path))
    for page in range(1, pages + 1):
        if heading:
            pdf.setFont("Helvetica-Bold", 24)
            pdf.drawString(72, 720, f"Heading {page}")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(72, 690, f"Sample page {page}")
        pdf.showPage()
    pdf.save()
    return path


def build_image(path: Path, color: str = "navy", size: tuple[int, int] = (120, 90)) -> Path:
    Image.new("RGB", size, color).save(path)
    return path


def build_table_pdf(path: Path, rows: list[list[str]] | None = None) -> Path:
    """Create a PDF holding one ruled table, which table detection can find."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

    data = rows or [
        ["Item", "Qty", "Price"],
        ["Widget", "2", "10.00"],
        ["Gadget", "1", "25.50"],
    ]
    table = Table(data)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    SimpleDocTemplate(str(path), pagesize=letter).build([table])
    return path


def build_scanned_pdf(path: Path, text: str = "SCANNED HELLO WORLD") -> Path:
    """Create an image-only PDF: the words exist as pixels, not as a text layer."""
    import fitz

    source = fitz.open()
    page = source.new_page()
    page.insert_text((72, 700), text, fontsize=28, fontname="helv")
    pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    source.close()

    scan = fitz.open()
    scan_page = scan.new_page(width=pixmap.width * 0.24, height=pixmap.height * 0.24)
    scan_page.insert_image(scan_page.rect, stream=pixmap.tobytes("png"))
    scan.save(str(path))
    scan.close()
    return path


def build_signature_image(path: Path) -> Path:
    from PIL import ImageDraw

    image = Image.new("RGBA", (400, 150), (255, 255, 255, 0))
    pen = ImageDraw.Draw(image)
    pen.line([(20, 120), (90, 30), (160, 120), (240, 40), (330, 110)], fill=(10, 20, 120, 255), width=6)
    image.save(path)
    return path


@pytest.fixture
def sample_pdf(workspace: Path) -> Path:
    return build_pdf(workspace / "sample.pdf", pages=3)


@pytest.fixture
def invoice_pdf(workspace: Path) -> Path:
    """A two-page PDF with searchable text used by the edit and redact tests."""
    from reportlab.pdfgen import canvas as pdf_canvas

    path = workspace / "invoice.pdf"
    pdf = pdf_canvas.Canvas(str(path))
    for page in range(1, 3):
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(72, 760, f"Invoice {page}")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(72, 730, "Account number 1234-5678")
        pdf.drawString(72, 710, "Secret Total 99.00")
        pdf.showPage()
    pdf.save()
    return path
