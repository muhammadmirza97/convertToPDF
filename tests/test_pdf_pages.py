from __future__ import annotations

import pytest
from pypdf import PdfReader

from src.pdf_pages import extract_pages, insert_pdf, remove_pages, reorder_pages, rotate_pdf
from src.pdf_tools import pdf_to_text
from tests.conftest import build_pdf


def _page_labels(path) -> list[str]:
    """Return the "Sample page N" text of each page, in order."""
    reader = PdfReader(str(path))
    labels = []
    for page in reader.pages:
        text = page.extract_text() or ""
        labels.append(text.strip().splitlines()[0] if text.strip() else "")
    return labels


def test_rotate_all_pages(sample_pdf, workspace):
    output = rotate_pdf(sample_pdf, workspace)

    reader = PdfReader(str(output))
    assert [page.rotation for page in reader.pages] == [90, 90, 90]
    assert PdfReader(str(sample_pdf)).pages[0].rotation == 0  # original untouched


def test_rotate_selected_pages_only(sample_pdf, workspace):
    output = rotate_pdf(sample_pdf, workspace, angle=180, pages="2")

    assert [page.rotation for page in PdfReader(str(output)).pages] == [0, 180, 0]


def test_rotate_rejects_bad_angle(sample_pdf, workspace):
    with pytest.raises(ValueError, match="90, 180 or 270"):
        rotate_pdf(sample_pdf, workspace, angle=45)


def test_extract_pages_keeps_requested_order(sample_pdf, workspace):
    outputs = extract_pages(sample_pdf, workspace, pages="3,1")

    assert len(outputs) == 1
    assert _page_labels(outputs[0]) == ["Sample page 3", "Sample page 1"]


def test_extract_pages_one_file_per_page(sample_pdf, workspace):
    outputs = extract_pages(sample_pdf, workspace, pages="1-2", separate_files=True)

    assert [path.name for path in outputs] == ["sample_page_001.pdf", "sample_page_002.pdf"]
    assert all(len(PdfReader(str(path)).pages) == 1 for path in outputs)


def test_extract_pages_requires_a_selection(sample_pdf, workspace):
    with pytest.raises(ValueError, match="pages to extract"):
        extract_pages(sample_pdf, workspace, pages="")


def test_remove_pages(sample_pdf, workspace):
    output = remove_pages(sample_pdf, workspace, pages="2")

    assert _page_labels(output) == ["Sample page 1", "Sample page 3"]


def test_remove_pages_refuses_to_empty_the_pdf(sample_pdf, workspace):
    with pytest.raises(ValueError, match="empty PDF"):
        remove_pages(sample_pdf, workspace, pages="1-3")


def test_remove_pages_rejects_out_of_range(sample_pdf, workspace):
    with pytest.raises(ValueError, match="between 1 and 3"):
        remove_pages(sample_pdf, workspace, pages="9")


def test_reorder_pages(sample_pdf, workspace):
    output = reorder_pages(sample_pdf, workspace, order="3,1,2")

    assert _page_labels(output) == ["Sample page 3", "Sample page 1", "Sample page 2"]


def test_reorder_requires_every_page(sample_pdf, workspace):
    with pytest.raises(ValueError, match="Missing page"):
        reorder_pages(sample_pdf, workspace, order="1,2")


def test_insert_pdf_at_position(sample_pdf, workspace):
    extra = build_pdf(workspace / "extra.pdf", pages=1)

    output = insert_pdf(sample_pdf, workspace, insert_file=extra, after_page=1)

    assert len(PdfReader(str(output)).pages) == 4
    text = pdf_to_text(output, workspace).read_text(encoding="utf-8")
    assert text.index("--- Page 2 ---") < text.index("--- Page 3 ---")


def test_insert_pdf_rejects_missing_file(sample_pdf, workspace):
    with pytest.raises(ValueError, match="not found"):
        insert_pdf(sample_pdf, workspace, insert_file=workspace / "nope.pdf")


def test_insert_pdf_rejects_bad_position(sample_pdf, workspace):
    extra = build_pdf(workspace / "extra.pdf", pages=1)

    with pytest.raises(ValueError, match="between 0 and 3"):
        insert_pdf(sample_pdf, workspace, insert_file=extra, after_page=9)
