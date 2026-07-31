from __future__ import annotations

import json

import fitz
import pytest

from src.pdf_forms import (
    create_form_field,
    fill_form,
    form_report,
    list_form_fields,
    parse_field_values,
)


@pytest.fixture
def form_pdf(sample_pdf, workspace):
    """A PDF carrying a text box, a checkbox and a dropdown on page 1."""
    text = create_form_field(
        sample_pdf, workspace, field_name="full_name", kind="Text box", x_mm=20, y_mm=30
    ).outputs[0]
    checkbox = create_form_field(
        text, workspace, field_name="agree", kind="Checkbox", x_mm=20, y_mm=45, width_mm=6, height_mm=6
    ).outputs[0]
    return create_form_field(
        checkbox,
        workspace,
        field_name="plan",
        kind="Dropdown",
        x_mm=20,
        y_mm=60,
        choices="Basic, Standard, Premium",
    ).outputs[0]


# --- creating fields --------------------------------------------------------


def test_create_text_field(sample_pdf, workspace):
    result = create_form_field(sample_pdf, workspace, field_name="full_name")

    fields = list_form_fields(result.outputs[0])
    assert [field.name for field in fields] == ["full_name"]
    assert fields[0].page_number == 1
    assert "text box field(s)" in result.note
    assert not list_form_fields(sample_pdf)  # original untouched


def test_create_field_on_several_pages_numbers_the_names(sample_pdf, workspace):
    result = create_form_field(sample_pdf, workspace, field_name="initials", pages="1-2")

    names = [field.name for field in list_form_fields(result.outputs[0])]
    assert names == ["initials_1", "initials_2"]


def test_create_dropdown_keeps_its_choices(sample_pdf, workspace):
    result = create_form_field(
        sample_pdf, workspace, field_name="plan", kind="Dropdown", choices="Basic, Premium"
    )

    field = list_form_fields(result.outputs[0])[0]
    assert field.choices == ("Basic", "Premium")
    assert field.value == "Basic"


def test_create_field_needs_a_name(sample_pdf, workspace):
    with pytest.raises(ValueError, match="name for the field"):
        create_form_field(sample_pdf, workspace, field_name="  ")


def test_dropdown_needs_two_choices(sample_pdf, workspace):
    with pytest.raises(ValueError, match="at least two choices"):
        create_form_field(sample_pdf, workspace, field_name="plan", kind="Dropdown", choices="Only")


def test_create_field_rejects_a_position_off_the_page(sample_pdf, workspace):
    with pytest.raises(ValueError, match="outside page"):
        create_form_field(sample_pdf, workspace, field_name="x", x_mm=900, y_mm=900)


def test_create_field_rejects_zero_size(sample_pdf, workspace):
    with pytest.raises(ValueError, match="greater than zero"):
        create_form_field(sample_pdf, workspace, field_name="x", width_mm=0)


# --- listing fields ---------------------------------------------------------


def test_form_report_writes_editable_json(form_pdf, workspace):
    result = form_report(form_pdf, workspace)

    payload = json.loads(result.outputs[0].read_text(encoding="utf-8"))
    assert set(payload) == {"full_name", "agree", "plan"}
    assert "Found 3 field(s)" in result.note


def test_form_report_explains_a_pdf_without_fields(sample_pdf, workspace):
    with pytest.raises(ValueError, match="no fillable form fields"):
        form_report(sample_pdf, workspace)


# --- filling ----------------------------------------------------------------


def test_fill_form_sets_values(form_pdf, workspace):
    result = fill_form(
        form_pdf, workspace, field_values="full_name=Mirza; agree=yes; plan=Premium"
    )

    values = {field.name: field.value for field in list_form_fields(result.outputs[0])}
    assert values["full_name"] == "Mirza"
    assert values["plan"] == "Premium"
    assert values["agree"] in ("Yes", "On", "True")
    assert "Filled 3 field(s)" in result.note


def test_fill_form_accepts_json(form_pdf, workspace):
    result = fill_form(form_pdf, workspace, field_values='{"full_name": "Ada"}')

    values = {field.name: field.value for field in list_form_fields(result.outputs[0])}
    assert values["full_name"] == "Ada"


def test_flatten_turns_fields_into_plain_text(form_pdf, workspace):
    result = fill_form(form_pdf, workspace, field_values="full_name=Mirza", flatten=True)

    output = result.outputs[0]
    assert not list_form_fields(output)          # no fillable fields remain
    with fitz.open(output) as document:
        assert "Mirza" in document.load_page(0).get_text()
    assert "flattened" in result.note


def test_fill_form_rejects_an_unknown_field(form_pdf, workspace):
    with pytest.raises(ValueError, match="no field named 'nickname'"):
        fill_form(form_pdf, workspace, field_values="nickname=Mir")


def test_fill_form_rejects_a_value_outside_the_dropdown(form_pdf, workspace):
    with pytest.raises(ValueError, match="not an option"):
        fill_form(form_pdf, workspace, field_values="plan=Enterprise")


def test_fill_form_explains_a_pdf_without_fields(sample_pdf, workspace):
    with pytest.raises(ValueError, match="no fillable form fields"):
        fill_form(sample_pdf, workspace, field_values="anything=1")


def test_fill_form_needs_values_or_flattening(form_pdf, workspace):
    with pytest.raises(ValueError, match="Enter the values to fill"):
        fill_form(form_pdf, workspace, field_values="")


def test_fill_form_can_flatten_without_new_values(form_pdf, workspace):
    result = fill_form(form_pdf, workspace, flatten=True)

    assert not list_form_fields(result.outputs[0])


# --- value parsing ----------------------------------------------------------


def test_parse_field_values_reads_pairs():
    assert parse_field_values("a=1; b = two") == {"a": "1", "b": "two"}


def test_parse_field_values_reads_json():
    assert parse_field_values('{"a": 1, "b": null}') == {"a": "1", "b": ""}


def test_parse_field_values_reads_newline_separated_pairs():
    assert parse_field_values("a=1\nb=2") == {"a": "1", "b": "2"}


def test_parse_field_values_rejects_broken_json():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_field_values('{"a": }')


def test_parse_field_values_rejects_a_pair_without_equals():
    with pytest.raises(ValueError, match="name=value"):
        parse_field_values("just a name")


def test_parse_field_values_ignores_blank_input():
    assert parse_field_values("   ") == {}
