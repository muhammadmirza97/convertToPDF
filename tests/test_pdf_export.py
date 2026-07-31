"""Tests for PDF to Excel and PDF to PowerPoint."""

from __future__ import annotations

import openpyxl
import pytest
from pptx import Presentation

from src.pdf_export import pdf_to_excel, pdf_to_powerpoint
from tests.conftest import build_scanned_pdf, build_table_pdf


def test_detected_tables_become_worksheets(workspace):
    source = build_table_pdf(workspace / "table.pdf")

    result = pdf_to_excel(source, workspace, mode="Detected tables")

    workbook = openpyxl.load_workbook(result.outputs[0])
    rows = [[cell.value for cell in row] for row in workbook[workbook.sheetnames[0]].iter_rows()]
    workbook.close()
    assert rows[0] == ["Item", "Qty", "Price"]
    assert ["Widget", "2", "10.00"] in rows
    assert "table(s)" in result.note


def test_text_lines_mode_writes_one_row_per_line(sample_pdf, workspace):
    result = pdf_to_excel(sample_pdf, workspace, mode="Text lines")

    workbook = openpyxl.load_workbook(result.outputs[0])
    assert len(workbook.sheetnames) == 3
    first = [cell.value for cell in next(workbook["page_1"].iter_rows())]
    workbook.close()
    assert first == ["Sample page 1"]


def test_excel_export_honours_page_selection(sample_pdf, workspace):
    result = pdf_to_excel(sample_pdf, workspace, mode="Text lines", pages="2")

    workbook = openpyxl.load_workbook(result.outputs[0])
    names = workbook.sheetnames
    workbook.close()
    assert names == ["page_2"]


def test_excel_export_explains_when_no_table_is_found(sample_pdf, workspace):
    with pytest.raises(ValueError, match="No tables were detected"):
        pdf_to_excel(sample_pdf, workspace, mode="Detected tables")


def test_excel_export_explains_a_scanned_pdf(workspace):
    scan = build_scanned_pdf(workspace / "scan.pdf")

    with pytest.raises(ValueError, match="needs OCR"):
        pdf_to_excel(scan, workspace, mode="Text lines")


def test_excel_export_rejects_an_unknown_mode(sample_pdf, workspace):
    with pytest.raises(ValueError, match="Excel export mode"):
        pdf_to_excel(sample_pdf, workspace, mode="magic")


def test_powerpoint_export_makes_one_slide_per_page(sample_pdf, workspace):
    result = pdf_to_powerpoint(sample_pdf, workspace, dpi=72)

    presentation = Presentation(str(result.outputs[0]))
    assert len(presentation.slides) == 3
    assert "3 slide(s)" in result.note


def test_powerpoint_export_puts_text_in_the_notes(sample_pdf, workspace):
    result = pdf_to_powerpoint(sample_pdf, workspace, dpi=72, include_notes=True)

    presentation = Presentation(str(result.outputs[0]))
    notes = presentation.slides[0].notes_slide.notes_text_frame.text
    assert "Sample page 1" in notes


def test_powerpoint_export_can_skip_notes(sample_pdf, workspace):
    result = pdf_to_powerpoint(sample_pdf, workspace, dpi=72, include_notes=False)

    presentation = Presentation(str(result.outputs[0]))
    assert presentation.slides[0].notes_slide.notes_text_frame.text.strip() == ""


def test_powerpoint_slide_size_follows_the_page(sample_pdf, workspace):
    result = pdf_to_powerpoint(sample_pdf, workspace, dpi=72)

    presentation = Presentation(str(result.outputs[0]))
    ratio = presentation.slide_height / presentation.slide_width
    assert 1.2 < ratio < 1.5  # portrait letter/A4 proportions


def test_powerpoint_export_rejects_a_silly_dpi(sample_pdf, workspace):
    with pytest.raises(ValueError, match="resolution"):
        pdf_to_powerpoint(sample_pdf, workspace, dpi=5000)
