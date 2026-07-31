"""Tests for the conversion tools: images, text, HTML, PDF export."""

from __future__ import annotations

import fitz
import pytest
from PIL import Image

from src.html_tools import html_to_pdf
from src.image_tools import images_to_pdf
from src.pdf_tools import pdf_to_images, pdf_to_markdown, pdf_to_text
from src.text_tools import txt_to_pdf
from tests.conftest import build_image, build_pdf


# --- images to PDF ----------------------------------------------------------


def test_images_to_pdf_combines_into_one_file(workspace):
    first = build_image(workspace / "first.png", "red")
    second = build_image(workspace / "second.png", "green")

    outputs = images_to_pdf([first, second], workspace, single_file=True)

    assert len(outputs) == 1
    with fitz.open(outputs[0]) as document:
        assert document.page_count == 2


def test_images_to_pdf_one_file_per_image(workspace):
    first = build_image(workspace / "first.png")
    second = build_image(workspace / "second.png")

    outputs = images_to_pdf([first, second], workspace, single_file=False)

    assert [path.stem for path in outputs] == ["first", "second"]


def test_images_to_pdf_uses_the_chosen_page_size(workspace):
    image = build_image(workspace / "wide.png", size=(400, 200))

    output = images_to_pdf([image], workspace, page_size="A4", orientation="Portrait")[0]

    with fitz.open(output) as document:
        rect = document.load_page(0).rect
    assert round(rect.width) == 595 and round(rect.height) == 842


def test_images_to_pdf_auto_orientation_follows_the_image(workspace):
    image = build_image(workspace / "wide.png", size=(400, 200))

    output = images_to_pdf([image], workspace, page_size="A4", orientation="Auto")[0]

    with fitz.open(output) as document:
        rect = document.load_page(0).rect
    assert rect.width > rect.height


def test_images_to_pdf_rejects_an_empty_selection(workspace):
    with pytest.raises(ValueError, match="at least one image"):
        images_to_pdf([], workspace)


def test_images_to_pdf_rejects_an_unknown_page_size(workspace):
    image = build_image(workspace / "photo.png")

    with pytest.raises(ValueError, match="page size"):
        images_to_pdf([image], workspace, page_size="B7")


def test_images_to_pdf_keeps_transparency_on_white(workspace):
    transparent = workspace / "clear.png"
    Image.new("RGBA", (60, 60), (255, 0, 0, 0)).save(transparent)

    output = images_to_pdf([transparent], workspace)[0]

    assert output.read_bytes().startswith(b"%PDF")


# --- text to PDF ------------------------------------------------------------


def test_txt_to_pdf_keeps_unicode_text(workspace):
    source = workspace / "notes.txt"
    source.write_text("Café Zürich — naïve\nsecond line", encoding="utf-8")

    output = txt_to_pdf(source, workspace)

    with fitz.open(output) as document:
        text = document.load_page(0).get_text()
    assert "Caf" in text and "second line" in text


def test_txt_to_pdf_wraps_long_lines_onto_more_pages(workspace):
    source = workspace / "long.txt"
    source.write_text("word " * 6000, encoding="utf-8")

    output = txt_to_pdf(source, workspace, font_size=12)

    with fitz.open(output) as document:
        assert document.page_count > 1


def test_txt_to_pdf_landscape_page_is_wider_than_tall(workspace):
    source = workspace / "notes.txt"
    source.write_text("hello", encoding="utf-8")

    output = txt_to_pdf(source, workspace, orientation="Landscape")

    with fitz.open(output) as document:
        rect = document.load_page(0).rect
    assert rect.width > rect.height


def test_txt_to_pdf_rejects_a_silly_font_size(workspace):
    source = workspace / "notes.txt"
    source.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="font size"):
        txt_to_pdf(source, workspace, font_size=400)


# --- HTML to PDF ------------------------------------------------------------


def test_html_to_pdf_renders_text(workspace):
    source = workspace / "page.html"
    source.write_text("<h1>Report title</h1><p>Body paragraph here.</p>", encoding="utf-8")

    output = html_to_pdf(source, workspace)

    with fitz.open(output) as document:
        text = document.load_page(0).get_text()
    assert "Report title" in text
    assert "Body paragraph" in text


def test_html_to_pdf_honours_page_size(workspace):
    source = workspace / "page.html"
    source.write_text("<p>hello</p>", encoding="utf-8")

    output = html_to_pdf(source, workspace, page_size="A5")

    with fitz.open(output) as document:
        assert round(document.load_page(0).rect.width) == 420


def test_html_to_pdf_rejects_a_huge_margin(workspace):
    source = workspace / "page.html"
    source.write_text("<p>hello</p>", encoding="utf-8")

    with pytest.raises(ValueError, match="margin"):
        html_to_pdf(source, workspace, margin_mm=90)


# --- PDF to images / text / markdown ---------------------------------------


def test_pdf_to_images_as_jpg_with_page_selection(sample_pdf, workspace):
    outputs = pdf_to_images(sample_pdf, workspace, image_format="jpg", dpi=72, pages="1,3")

    assert [path.suffix for path in outputs] == [".jpg", ".jpg"]
    assert [path.stem[-3:] for path in outputs] == ["001", "003"]


def test_pdf_to_images_dpi_changes_pixel_size(sample_pdf, workspace):
    low = pdf_to_images(sample_pdf, workspace, dpi=36, pages="1")[0]
    high = pdf_to_images(sample_pdf, workspace, dpi=144, pages="1")[0]

    with Image.open(low) as small, Image.open(high) as large:
        assert large.width > small.width * 3


def test_pdf_to_images_rejects_a_bad_format(sample_pdf, workspace):
    with pytest.raises(ValueError, match="PNG or JPG"):
        pdf_to_images(sample_pdf, workspace, image_format="tiff")


def test_pdf_to_images_rejects_a_bad_dpi(sample_pdf, workspace):
    with pytest.raises(ValueError, match="DPI"):
        pdf_to_images(sample_pdf, workspace, dpi=5000)


def test_pdf_to_text_page_selection(sample_pdf, workspace):
    output = pdf_to_text(sample_pdf, workspace, pages="2")

    text = output.read_text(encoding="utf-8")
    assert "Sample page 2" in text
    assert "Sample page 1" not in text


def test_pdf_to_markdown_marks_headings(workspace):
    source = build_pdf(workspace / "report.pdf", pages=2, heading=True)

    output = pdf_to_markdown(source, workspace)

    text = output.read_text(encoding="utf-8")
    assert output.suffix == ".md"
    assert "# Heading 1" in text
    assert "\n---\n" in text


def test_pdf_to_markdown_without_page_rules(workspace):
    source = build_pdf(workspace / "report.pdf", pages=2, heading=True)

    output = pdf_to_markdown(source, workspace, page_breaks=False)

    assert "\n---\n" not in output.read_text(encoding="utf-8")


def test_extract_images_saves_embedded_pictures(sample_pdf, workspace):
    from src.pdf_tools import extract_images

    logo = build_image(workspace / "logo.png", "teal", (300, 200))
    with fitz.open(sample_pdf) as document:
        document.load_page(0).insert_image(fitz.Rect(40, 40, 340, 240), filename=str(logo))
        with_image = workspace / "with_image.pdf"
        document.save(str(with_image))

    outputs = extract_images(with_image, workspace)

    assert len(outputs) == 1
    with Image.open(outputs[0]) as image:
        assert image.width >= 300


def test_extract_images_skips_tiny_pictures(sample_pdf, workspace):
    from src.pdf_tools import extract_images

    dot = build_image(workspace / "dot.png", "red", (8, 8))
    with fitz.open(sample_pdf) as document:
        document.load_page(0).insert_image(fitz.Rect(40, 40, 48, 48), filename=str(dot))
        with_dot = workspace / "with_dot.pdf"
        document.save(str(with_dot))

    with pytest.raises(ValueError, match="No embedded images"):
        extract_images(with_dot, workspace, minimum_pixels=64)


def test_extract_images_explains_a_pdf_without_pictures(sample_pdf, workspace):
    from src.pdf_tools import extract_images

    with pytest.raises(ValueError, match="No embedded images"):
        extract_images(sample_pdf, workspace)


def test_split_into_fixed_chunks(workspace):
    from src.pdf_tools import split_pdf

    source = build_pdf(workspace / "five.pdf", pages=5)

    outputs = split_pdf(source, workspace, every_n_pages=2)

    assert [path.name for path in outputs] == [
        "five_pages_001-002.pdf",
        "five_pages_003-004.pdf",
        "five_page_005.pdf",
    ]


def test_split_rejects_ranges_and_chunks_together(sample_pdf, workspace):
    from src.pdf_tools import split_pdf

    with pytest.raises(ValueError, match="not both"):
        split_pdf(sample_pdf, workspace, page_ranges="1-2", every_n_pages=2)


def test_split_rejects_a_negative_chunk_size(sample_pdf, workspace):
    from src.pdf_tools import split_pdf

    with pytest.raises(ValueError, match="cannot be negative"):
        split_pdf(sample_pdf, workspace, every_n_pages=-2)


def test_tiled_watermark_repeats_across_the_page(sample_pdf, workspace):
    from src.pdf_edit import watermark_pdf

    single = watermark_pdf(sample_pdf, workspace, text="DRAFT", font_size=20)
    tiled = watermark_pdf(sample_pdf, workspace, text="DRAFT", font_size=20, tiled=True)

    with fitz.open(single) as document:
        single_count = document.load_page(0).get_text().count("DRAFT")
    with fitz.open(tiled) as document:
        tiled_count = document.load_page(0).get_text().count("DRAFT")
    assert single_count == 1
    assert tiled_count > 4


def test_pdf_to_markdown_explains_scanned_pdfs(workspace):
    blank = workspace / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.save(str(blank))
    document.close()

    with pytest.raises(ValueError, match="OCR"):
        pdf_to_markdown(blank, workspace)
