"""Form workspace: show a PDF's fillable fields and type into them."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from .pdf_forms import TRUE_WORDS, FormField, list_form_fields


class FormWorkspace(ctk.CTkToplevel):
    """Modal window listing every field in a PDF form, with an editor per field."""

    def __init__(self, parent, pdf_path: Path, *, password: str = "", on_apply=None) -> None:
        super().__init__(parent)
        self.title(f"Fill form - {pdf_path.name}")
        self.geometry("760x600")
        self.minsize(600, 420)

        self.pdf_path = pdf_path
        self.on_apply = on_apply
        self.fields: list[FormField] = list_form_fields(pdf_path, password=password or None)
        self.variables: dict[str, tk.Variable] = {}
        self.status = tk.StringVar()

        self._build_ui()
        self.transient(parent)
        self.after(120, self._grab)

    def _grab(self) -> None:
        try:
            self.grab_set()
        except Exception:
            pass

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        summary = (
            f"{len(self.fields)} field(s) found"
            if self.fields
            else "This PDF has no fillable fields. Use Create form field first."
        )
        ctk.CTkLabel(header, text=summary, anchor="w").grid(row=0, column=0, sticky="w", padx=14, pady=12)

        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Fields")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        self.list_frame.grid_columnconfigure(1, weight=1)

        for row, field in enumerate(self.fields):
            self._build_field_row(row, field)

        footer = ctk.CTkFrame(self, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, textvariable=self.status, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=12, pady=12
        )
        ctk.CTkButton(footer, text="Clear all", width=90, command=self._clear).grid(
            row=0, column=1, padx=4, pady=12
        )
        ctk.CTkButton(footer, text="Cancel", width=90, command=self.destroy).grid(
            row=0, column=2, padx=4, pady=12
        )
        ctk.CTkButton(footer, text="Use these values", width=140, command=self._apply).grid(
            row=0, column=3, padx=(4, 12), pady=12
        )

    def _build_field_row(self, row: int, field: FormField) -> None:
        label = f"{field.name}   (page {field.page_number}, {field.kind.lower()})"
        if field.read_only:
            label += "  read-only"
        ctk.CTkLabel(self.list_frame, text=label, anchor="w").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )

        state = "disabled" if field.read_only else "normal"
        if field.is_checkbox:
            variable = tk.BooleanVar(value=field.value.strip().lower() in TRUE_WORDS)
            widget = ctk.CTkSwitch(self.list_frame, text="", variable=variable, state=state)
        elif field.choices:
            variable = tk.StringVar(value=field.value or field.choices[0])
            widget = ctk.CTkOptionMenu(
                self.list_frame, values=list(field.choices), variable=variable, state=state
            )
        else:
            variable = tk.StringVar(value=field.value)
            widget = ctk.CTkEntry(self.list_frame, textvariable=variable, state=state)

        widget.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        self.variables[field.name] = variable

    def _clear(self) -> None:
        for field in self.fields:
            if field.read_only:
                continue
            variable = self.variables[field.name]
            variable.set(False if field.is_checkbox else "")
        self.status.set("Cleared. Values are only saved when you press Use these values.")

    def collect(self) -> dict[str, str]:
        """Return the edited values, skipping read-only fields."""
        values: dict[str, str] = {}
        for field in self.fields:
            if field.read_only:
                continue
            raw = self.variables[field.name].get()
            values[field.name] = "yes" if raw is True else ("no" if raw is False else str(raw))
        return values

    def _apply(self) -> None:
        if not self.fields:
            self.status.set("There are no fields to fill.")
            return
        if self.on_apply:
            self.on_apply(json.dumps(self.collect(), ensure_ascii=False))
        self.destroy()
