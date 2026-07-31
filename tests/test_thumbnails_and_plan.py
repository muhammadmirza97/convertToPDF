"""Thumbnail rendering, page plans, and the plan text the workspace produces."""

from __future__ import annotations

import pytest
from pypdf import PdfReader

from src.gui_organize import PlanItem, plan_to_text
from src.pdf_pages import apply_page_plan
from src.thumbnails import render_thumbnails


def test_thumbnails_are_rendered_for_every_page(sample_pdf):
    thumbnails = render_thumbnails(sample_pdf, max_edge=120)

    assert [thumb.index for thumb in thumbnails] == [0, 1, 2]
    assert all(thumb.png_bytes.startswith(b"\x89PNG") for thumb in thumbnails)
    assert all(max(thumb.width, thumb.height) <= 121 for thumb in thumbnails)


def test_thumbnails_open_as_images(sample_pdf):
    thumbnail = render_thumbnails(sample_pdf, max_edge=100)[0]

    with thumbnail.to_image() as image:
        assert image.size == (thumbnail.width, thumbnail.height)


def test_thumbnail_limit_is_respected(sample_pdf):
    assert len(render_thumbnails(sample_pdf, max_edge=80, limit=2)) == 2


def test_thumbnails_reject_a_silly_size(sample_pdf):
    with pytest.raises(ValueError, match="between 40 and 600"):
        render_thumbnails(sample_pdf, max_edge=5)


def test_plan_text_only_writes_rotation_when_needed():
    items = [PlanItem(2, 90), PlanItem(0), PlanItem(1, 180)]

    assert plan_to_text(items) == "3:90,1,2:180"


def test_apply_page_plan_reorders_rotates_and_drops(sample_pdf, workspace):
    output = apply_page_plan(sample_pdf, workspace, plan="3:90,1")

    pages = PdfReader(str(output)).pages
    assert len(pages) == 2
    assert pages[0].rotation == 90
    assert pages[1].rotation == 0
    assert "Sample page 3" in (pages[0].extract_text() or "")
    assert len(PdfReader(str(sample_pdf)).pages) == 3  # original untouched


def test_apply_page_plan_can_duplicate_a_page(sample_pdf, workspace):
    output = apply_page_plan(sample_pdf, workspace, plan="1,1,1")

    assert len(PdfReader(str(output)).pages) == 3


def test_apply_page_plan_rejects_an_empty_plan(sample_pdf, workspace):
    with pytest.raises(ValueError, match="plan is empty"):
        apply_page_plan(sample_pdf, workspace, plan="  ")


def test_apply_page_plan_rejects_a_page_out_of_range(sample_pdf, workspace):
    with pytest.raises(ValueError, match="but the PDF has 3"):
        apply_page_plan(sample_pdf, workspace, plan="9")


def test_apply_page_plan_rejects_a_bad_rotation(sample_pdf, workspace):
    with pytest.raises(ValueError, match="0, 90, 180 or 270"):
        apply_page_plan(sample_pdf, workspace, plan="1:45")


def test_apply_page_plan_rejects_nonsense(sample_pdf, workspace):
    with pytest.raises(ValueError, match="look like 3 or 3:90"):
        apply_page_plan(sample_pdf, workspace, plan="first page")
