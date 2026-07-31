from __future__ import annotations

import fitz
import pytest

from src.pdf_annotate import add_image, add_shape, add_text, highlight_text
from tests.conftest import build_image


def _annotation_types(path, page_index=0) -> list[str]:
    with fitz.open(path) as document:
        return [annotation.type[1] for annotation in document.load_page(page_index).annots()]


def _page_text(path, page_index=0) -> str:
    with fitz.open(path) as document:
        return document.load_page(page_index).get_text()


# --- highlight --------------------------------------------------------------


def test_highlight_marks_every_occurrence(invoice_pdf, workspace):
    result = highlight_text(invoice_pdf, workspace, search_text="Account number")

    assert "Marked 2 occurrence(s)" in result.note
    assert "Highlight" in _annotation_types(result.outputs[0])
    assert not _annotation_types(invoice_pdf)  # original untouched


def test_strikeout_style(invoice_pdf, workspace):
    result = highlight_text(invoice_pdf, workspace, search_text="Secret Total", style="Strikeout")

    assert "StrikeOut" in _annotation_types(result.outputs[0])


def test_highlight_respects_page_selection(invoice_pdf, workspace):
    result = highlight_text(invoice_pdf, workspace, search_text="Invoice", pages="2")

    assert not _annotation_types(result.outputs[0], 0)
    assert _annotation_types(result.outputs[0], 1)


def test_highlight_needs_search_text(invoice_pdf, workspace):
    with pytest.raises(ValueError, match="text you want to mark"):
        highlight_text(invoice_pdf, workspace, search_text="  ")


def test_highlight_explains_when_text_is_absent(invoice_pdf, workspace):
    with pytest.raises(ValueError, match="was not found"):
        highlight_text(invoice_pdf, workspace, search_text="zebra crossing")


def test_highlight_rejects_an_unknown_style(invoice_pdf, workspace):
    with pytest.raises(ValueError, match="mark style"):
        highlight_text(invoice_pdf, workspace, search_text="Invoice", style="Sparkle")


# --- add text ---------------------------------------------------------------


def test_add_text_writes_on_the_page(sample_pdf, workspace):
    output = add_text(sample_pdf, workspace, text="APPROVED", x_mm=20, y_mm=30)

    assert "APPROVED" in _page_text(output)


def test_add_text_supports_multiple_lines(sample_pdf, workspace):
    output = add_text(sample_pdf, workspace, text="First\\nSecond", x_mm=20, y_mm=30)

    text = _page_text(output)
    assert "First" in text and "Second" in text


def test_add_text_needs_content(sample_pdf, workspace):
    with pytest.raises(ValueError, match="text you want to add"):
        add_text(sample_pdf, workspace, text="")


def test_add_text_rejects_a_position_off_the_page(sample_pdf, workspace):
    with pytest.raises(ValueError, match="outside page"):
        add_text(sample_pdf, workspace, text="hello", x_mm=900, y_mm=900)


def test_add_text_rejects_a_silly_font_size(sample_pdf, workspace):
    with pytest.raises(ValueError, match="font size"):
        add_text(sample_pdf, workspace, text="hello", font_size=900)


# --- shapes -----------------------------------------------------------------


@pytest.mark.parametrize("shape", ["Rectangle", "Ellipse", "Line", "Arrow"])
def test_every_shape_draws(sample_pdf, workspace, shape):
    output = add_shape(sample_pdf, workspace, shape=shape, x_mm=20, y_mm=20)

    with fitz.open(output) as document:
        assert document.load_page(0).get_drawings()


def test_filled_shape_is_accepted(sample_pdf, workspace):
    output = add_shape(sample_pdf, workspace, shape="Rectangle", fill=True, color="Blue")

    assert output.exists()


def test_shape_rejects_zero_size(sample_pdf, workspace):
    with pytest.raises(ValueError, match="greater than zero"):
        add_shape(sample_pdf, workspace, width_mm=0, height_mm=10)


def test_shape_rejects_an_unknown_shape(sample_pdf, workspace):
    with pytest.raises(ValueError, match="a shape"):
        add_shape(sample_pdf, workspace, shape="Hexagram")


# --- images -----------------------------------------------------------------


def test_add_image_places_a_picture(sample_pdf, workspace):
    logo = build_image(workspace / "logo.png", "teal", (200, 100))

    output = add_image(sample_pdf, workspace, image_file=logo, x_mm=20, y_mm=20, width_mm=40)

    with fitz.open(output) as document:
        assert document.load_page(0).get_images()


def test_add_image_needs_a_file(sample_pdf, workspace):
    with pytest.raises(ValueError, match="image you want to place"):
        add_image(sample_pdf, workspace)


def test_add_image_rejects_a_missing_file(sample_pdf, workspace):
    with pytest.raises(ValueError, match="not found"):
        add_image(sample_pdf, workspace, image_file=workspace / "ghost.png")


def test_add_image_rejects_a_non_image(sample_pdf, workspace):
    text = workspace / "notes.txt"
    text.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="PNG, JPG or JPEG"):
        add_image(sample_pdf, workspace, image_file=text)
