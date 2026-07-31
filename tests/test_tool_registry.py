from __future__ import annotations

import pytest

from src.config import CATEGORIES, SUPPORTED_INPUT_EXTENSIONS
from src.tool_registry import (
    KIND_BOOL,
    KIND_CHOICE,
    KIND_FLOAT,
    KIND_INT,
    TOOLS,
    Option,
    find_tool,
    get_tool,
    tools_for_extension,
    tools_in_category,
)


def test_tool_ids_are_unique():
    ids = [tool.id for tool in TOOLS]

    assert len(ids) == len(set(ids))


def test_every_tool_belongs_to_a_known_category():
    assert all(tool.category in CATEGORIES for tool in TOOLS)


def test_every_tool_accepts_only_supported_extensions():
    for tool in TOOLS:
        assert tool.extensions
        assert tool.extensions <= set(SUPPORTED_INPUT_EXTENSIONS), tool.id


def test_every_tool_has_a_description_and_processor():
    for tool in TOOLS:
        assert tool.description.strip(), tool.id
        assert callable(tool.processor), tool.id


def test_choice_defaults_are_valid_choices():
    for tool in TOOLS:
        for option in tool.options:
            if option.kind == KIND_CHOICE:
                assert option.default in option.choices, f"{tool.id}.{option.key}"


def test_option_keys_are_unique_per_tool():
    for tool in TOOLS:
        keys = [option.key for option in tool.options]
        assert len(keys) == len(set(keys)), tool.id


def test_every_category_has_at_least_one_tool():
    for category in CATEGORIES:
        assert tools_in_category(category), category


def test_get_tool_accepts_id_and_label():
    assert get_tool("rotate_pdf").id == "rotate_pdf"
    assert get_tool("Rotate pages").id == "rotate_pdf"


def test_get_tool_label_lookup_ignores_case_and_spacing():
    assert get_tool("  merge pdfs ").id == "merge_pdfs"
    assert get_tool("Auto convert to PDF").id == "auto_to_pdf"


def test_get_tool_rejects_unknown_names():
    with pytest.raises(ValueError, match="Unknown tool"):
        get_tool("teleport_pdf")
    assert find_tool("teleport_pdf") is None


def test_tools_for_extension_finds_pdf_tools():
    ids = {tool.id for tool in tools_for_extension("pdf")}

    assert {"merge_pdfs", "rotate_pdf", "compress_pdf", "protect_pdf"} <= ids


def test_option_coercion_by_kind():
    assert Option("a", "A", KIND_INT, default=1).coerce("42") == 42
    assert Option("a", "A", KIND_FLOAT, default=1.0).coerce("2.5") == 2.5
    assert Option("a", "A", KIND_BOOL, default=False).coerce("true") is True
    assert Option("a", "A", KIND_BOOL, default=True).coerce("no") is False
    assert Option("a", "A", KIND_CHOICE, default="png", choices=("png", "jpg")).coerce("JPG") == "jpg"


def test_blank_numeric_option_falls_back_to_default():
    assert Option("a", "A", KIND_INT, default=7).coerce("") == 7


def test_bad_numeric_option_reports_the_label():
    with pytest.raises(ValueError, match="Font size must be a whole number"):
        Option("font_size", "Font size", KIND_INT, default=10).coerce("big")


def test_bad_choice_lists_the_allowed_values():
    option = Option("image_format", "Image format", KIND_CHOICE, default="png", choices=("png", "jpg"))

    with pytest.raises(ValueError, match="png, jpg"):
        option.coerce("bmp")


def test_coerce_options_fills_missing_keys_with_defaults():
    tool = get_tool("pdf_to_images")

    values = tool.coerce_options({"dpi": "72"})

    assert values["dpi"] == 72
    assert values["image_format"] == "png"
    assert set(values) == {option.key for option in tool.options}


def test_every_declared_dependency_has_a_message_and_label():
    from src.file_validation import DEPENDENCY_LABELS, DEPENDENCY_MESSAGES

    for tool in TOOLS:
        if tool.requires:
            assert tool.requires in DEPENDENCY_MESSAGES, tool.id
            assert tool.requires in DEPENDENCY_LABELS, tool.id


def test_workspace_tools_have_the_option_the_workspace_fills():
    filled_option = {"organize": "plan", "form": "field_values"}

    for tool in TOOLS:
        if tool.workspace:
            assert tool.workspace in filled_option, f"{tool.id} names an unknown workspace"
            assert tool.option(filled_option[tool.workspace]) is not None, tool.id


def test_processor_accepts_every_registered_option():
    """A registry option with no matching function argument would be silently ignored."""
    import inspect

    for tool in TOOLS:
        signature = inspect.signature(tool.processor)
        accepts_extra = any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
        if accepts_extra:
            continue
        for option in tool.options:
            assert option.key in signature.parameters, f"{tool.id}.{option.key}"


def test_ilovepdf_style_tool_coverage():
    """The tools a user coming from an online PDF service expects to find."""
    expected = {
        "merge_pdfs",
        "split_pdf",
        "compress_pdf",
        "pdf_to_word",
        "pdf_to_powerpoint",
        "pdf_to_excel",
        "office_to_pdf",
        "pdf_to_images",
        "images_to_pdf",
        "html_to_pdf",
        "pdf_to_pdfa",
        "rotate_pdf",
        "remove_pages",
        "extract_pages",
        "organize_pdf",
        "crop_pdf",
        "page_numbers",
        "watermark_pdf",
        "protect_pdf",
        "unlock_pdf",
        "redact_pdf",
        "sign_pdf",
        "compare_pdfs",
        "repair_pdf",
        "ocr_pdf",
        "add_text",
        "add_image",
        "add_shape",
        "highlight_text",
    }

    assert expected <= set(tool.id for tool in TOOLS)


def test_coerce_options_ignores_unknown_keys():
    tool = get_tool("rotate_pdf")

    values = tool.coerce_options({"nonsense": "1"})

    assert "nonsense" not in values
