"""PDF form support: read fields, fill them, flatten them, and create simple fields."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import fitz

from .choices import match_choice
from .output_paths import safe_output_path
from .pdf_edit import COLORS, MM_TO_POINTS
from .pdf_tools import open_document, parse_page_list
from .tool_result import ToolOutput


FIELD_KINDS = ("Text box", "Checkbox", "Dropdown")

_KIND_TO_TYPE = {
    "Text box": fitz.PDF_WIDGET_TYPE_TEXT,
    "Checkbox": fitz.PDF_WIDGET_TYPE_CHECKBOX,
    "Dropdown": fitz.PDF_WIDGET_TYPE_COMBOBOX,
}

TRUE_WORDS = {"1", "true", "yes", "on", "x", "checked"}


@dataclass
class FormField:
    page_number: int          # 1-based, for display
    name: str
    kind: str                 # PyMuPDF field type string, such as "Text"
    value: str
    choices: tuple[str, ...] = ()
    read_only: bool = False

    @property
    def is_checkbox(self) -> bool:
        return self.kind.lower().startswith("check")


def list_form_fields(input_path: str | Path, *, password: str | None = None) -> list[FormField]:
    """Return every fillable field in the PDF, in page order."""
    document = open_document(input_path, password)
    fields: list[FormField] = []
    try:
        for index in range(document.page_count):
            page = document.load_page(index)
            for widget in page.widgets() or []:
                if not widget.field_name:
                    continue
                fields.append(
                    FormField(
                        page_number=index + 1,
                        name=widget.field_name,
                        kind=widget.field_type_string or "Text",
                        value="" if widget.field_value is None else str(widget.field_value),
                        choices=tuple(widget.choice_values or ()),
                        read_only=bool(widget.field_flags & 1),
                    )
                )
    finally:
        document.close()
    return fields


def parse_field_values(spec: str | None) -> dict[str, str]:
    """Parse field values from JSON, or from simple `name=value` lines."""
    text = (spec or "").strip()
    if not text:
        return {}

    if text.startswith("{"):
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"The field values are not valid JSON: {exc}") from None
        if not isinstance(loaded, dict):
            raise ValueError("JSON field values must be an object of name and value pairs.")
        return {str(key): "" if value is None else str(value) for key, value in loaded.items()}

    values: dict[str, str] = {}
    for chunk in text.replace("\n", ";").split(";"):
        item = chunk.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"Use name=value for each field, not {item!r}.")
        name, value = item.split("=", 1)
        values[name.strip()] = value.strip()
    return values


def _apply_value(widget: fitz.Widget, value: str) -> None:
    if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
        wanted = value.strip().lower() in TRUE_WORDS
        widget.field_value = wanted
    elif widget.field_type == fitz.PDF_WIDGET_TYPE_COMBOBOX:
        allowed = list(widget.choice_values or ())
        if allowed and value not in allowed:
            match = next((item for item in allowed if item.lower() == value.strip().lower()), None)
            if match is None:
                raise ValueError(
                    f"'{value}' is not an option for {widget.field_name}. "
                    f"Choose one of: {', '.join(allowed)}."
                )
            value = match
        widget.field_value = value
    else:
        widget.field_value = value
    widget.update()


def _flatten_page(page: fitz.Page) -> None:
    """Draw each field's value as plain text, then delete the field."""
    for widget in list(page.widgets() or []):
        value = widget.field_value
        if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
            text = "X" if value in (True, "Yes", "On", "1") else ""
        else:
            text = "" if value is None else str(value)
        rect = widget.rect
        if text:
            size = widget.text_fontsize or 0
            if not size:
                size = max(6.0, min(11.0, rect.height * 0.6))
            page.insert_text(
                fitz.Point(rect.x0 + 2, rect.y1 - max(2.0, rect.height * 0.25)),
                text,
                fontname="helv",
                fontsize=size,
                color=(0, 0, 0),
                overlay=True,
            )
        page.delete_widget(widget)


def fill_form(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    field_values: str = "",
    flatten: bool = False,
    password: str | None = None,
) -> ToolOutput:
    """Fill named form fields, optionally flattening them into plain page content."""
    values = parse_field_values(field_values)
    source = Path(input_path)

    document = open_document(source, password)
    try:
        known = {
            widget.field_name
            for index in range(document.page_count)
            for widget in document.load_page(index).widgets() or []
            if widget.field_name
        }
        if not known:
            raise ValueError(
                f"{source.name} has no fillable form fields. "
                "Use Add text, or Create form field, instead."
            )

        unknown = [name for name in values if name not in known]
        if unknown:
            available = ", ".join(sorted(known)) or "none"
            raise ValueError(
                f"{source.name} has no field named '{unknown[0]}'. Fields found: {available}."
            )
        if not values and not flatten:
            raise ValueError(
                "Enter the values to fill, as name=value lines or JSON, "
                "or turn on Flatten to lock the current values."
            )

        filled = 0
        for index in range(document.page_count):
            page = document.load_page(index)
            for widget in page.widgets() or []:
                if widget.field_name in values:
                    _apply_value(widget, values[widget.field_name])
                    filled += 1
            if flatten:
                _flatten_page(page)

        output_path = safe_output_path(output_dir, f"{source.stem}_filled", ".pdf")
        document.save(str(output_path), garbage=3, deflate=True)
    finally:
        document.close()

    note = f"Filled {filled} field(s)"
    if flatten:
        note += "; fields flattened, so they can no longer be edited"
    return ToolOutput([output_path], note)


def create_form_field(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    field_name: str = "",
    kind: str = "Text box",
    x_mm: float = 20.0,
    y_mm: float = 20.0,
    width_mm: float = 60.0,
    height_mm: float = 8.0,
    initial_value: str = "",
    choices: str = "",
    border_color: str = "Gray",
    pages: str | None = "",
    password: str | None = None,
) -> ToolOutput:
    """Add a simple text box, checkbox or dropdown that can be filled later."""
    name = (field_name or "").strip()
    if not name:
        raise ValueError("Enter a name for the field, such as full_name.")
    wanted = match_choice(kind, FIELD_KINDS, "a field kind")
    if float(width_mm) <= 0 or float(height_mm) <= 0:
        raise ValueError("Field width and height must be greater than zero.")

    options = [item.strip() for item in (choices or "").split(",") if item.strip()]
    if wanted == "Dropdown" and len(options) < 2:
        raise ValueError("A dropdown needs at least two choices, separated by commas.")

    source = Path(input_path)
    document = open_document(source, password)
    added = 0
    try:
        selected = parse_page_list(pages if pages and str(pages).strip() else "1", document.page_count)
        for position, page_index in enumerate(selected, start=1):
            page = document.load_page(page_index)
            left, top = float(x_mm) * MM_TO_POINTS, float(y_mm) * MM_TO_POINTS
            rect = fitz.Rect(
                left,
                top,
                left + float(width_mm) * MM_TO_POINTS,
                top + float(height_mm) * MM_TO_POINTS,
            )
            if not rect.intersects(page.rect):
                raise ValueError(f"That position is outside page {page_index + 1}.")

            widget = fitz.Widget()
            widget.field_type = _KIND_TO_TYPE[wanted]
            # One field name per page, so several pages do not share one value.
            widget.field_name = name if len(selected) == 1 else f"{name}_{position}"
            widget.rect = rect
            widget.border_color = COLORS[match_choice(border_color, COLORS, "a border colour")]
            widget.border_width = 0.8
            widget.text_fontsize = 10
            if wanted == "Dropdown":
                widget.choice_values = options
                widget.field_value = initial_value.strip() or options[0]
            elif wanted == "Checkbox":
                widget.field_value = initial_value.strip().lower() in TRUE_WORDS
            else:
                widget.field_value = initial_value
            page.add_widget(widget)
            added += 1

        output_path = safe_output_path(output_dir, f"{source.stem}_form", ".pdf")
        document.save(str(output_path), garbage=3, deflate=True)
    finally:
        document.close()

    return ToolOutput([output_path], f"Added {added} {wanted.lower()} field(s)")


def form_report(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    password: str | None = None,
) -> ToolOutput:
    """Write the PDF's fillable fields to a JSON file you can edit and feed back in."""
    source = Path(input_path)
    fields = list_form_fields(source, password=password)
    if not fields:
        raise ValueError(f"{source.name} has no fillable form fields.")

    payload = {field.name: field.value for field in fields}
    output_path = safe_output_path(output_dir, f"{source.stem}_fields", ".json")
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    described = ", ".join(f"{field.name} ({field.kind})" for field in fields[:6])
    if len(fields) > 6:
        described += f" and {len(fields) - 6} more"
    return ToolOutput([output_path], f"Found {len(fields)} field(s): {described}")
