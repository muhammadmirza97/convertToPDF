"""GUI smoke test. Skipped automatically when Tk is unavailable on this machine."""

from __future__ import annotations

import tkinter as tk

import pytest

from src.tool_registry import TOOLS


def _new_app():
    """Build the dashboard, or skip when Tk itself cannot start.

    A missing display or a broken Tcl installation is an environment problem, not a
    product defect, so those runs skip instead of failing the suite.
    """
    from src.app import LocalPDFToolboxApp

    try:
        return LocalPDFToolboxApp()
    except tk.TclError as exc:
        pytest.skip(f"Tk is not usable here: {exc}")


def test_dashboard_builds_and_lists_every_available_tool():
    app = _new_app()
    try:
        app.update_idletasks()
        assert set(app.tool_buttons) == {tool.id for tool in TOOLS}
        assert app.tool is not None
    finally:
        app.destroy()


def test_selecting_every_tool_builds_its_option_form():
    app = _new_app()
    try:
        for tool in TOOLS:
            app._select_tool(tool)
            app.update_idletasks()
            assert set(app.option_vars) == {option.key for option in tool.options}
            # Collected values must survive coercion without raising.
            tool.coerce_options(app._collect_options())
    finally:
        app.destroy()


def test_workspace_button_appears_only_for_workspace_tools():
    from src.tool_registry import get_tool

    app = _new_app()
    try:
        app._select_tool(get_tool("organize_pdf"))
        app.update_idletasks()
        assert app.workspace_button.winfo_manager()

        app._select_tool(get_tool("rotate_pdf"))
        app.update_idletasks()
        assert not app.workspace_button.winfo_manager()
    finally:
        app.destroy()


def test_organize_workspace_builds_a_page_plan(sample_pdf):
    from src.gui_organize import OrganizeWorkspace

    app = _new_app()
    captured: dict[str, str] = {}
    try:
        workspace_window = OrganizeWorkspace(
            app, sample_pdf, on_apply=lambda plan: captured.setdefault("plan", plan)
        )
        app.update_idletasks()
        assert len(workspace_window.items) == 3

        workspace_window._toggle(0)          # select page 1
        workspace_window._rotate(90)
        workspace_window._move(1)            # swap it with page 2
        workspace_window._select_none()
        workspace_window._toggle(2)          # select the last tile
        workspace_window._delete()
        workspace_window._apply()
        app.update_idletasks()

        assert captured["plan"] == "2,1:90"
    finally:
        app.destroy()


def test_organize_workspace_keeps_at_least_one_page(sample_pdf):
    from src.gui_organize import OrganizeWorkspace

    app = _new_app()
    try:
        window = OrganizeWorkspace(app, sample_pdf)
        app.update_idletasks()
        window._select_all()
        window._delete()

        assert len(window.items) == 3
        assert "at least one page" in window.status.get()
    finally:
        app.destroy()


def test_applying_a_plan_fills_the_tool_option(sample_pdf):
    from src.tool_registry import get_tool

    app = _new_app()
    try:
        app._select_tool(get_tool("organize_pdf"))
        app._apply_page_plan("3,1:90")

        assert app.option_vars["plan"].get() == "3,1:90"
    finally:
        app.destroy()


def test_form_workspace_lists_fields_and_returns_json(sample_pdf, workspace):
    import json

    from src.gui_forms import FormWorkspace
    from src.pdf_forms import create_form_field

    form_pdf = create_form_field(
        sample_pdf, workspace, field_name="full_name", kind="Text box"
    ).outputs[0]

    app = _new_app()
    captured: dict[str, str] = {}
    try:
        window = FormWorkspace(
            app, form_pdf, on_apply=lambda values: captured.setdefault("values", values)
        )
        app.update_idletasks()
        assert [field.name for field in window.fields] == ["full_name"]

        window.variables["full_name"].set("Mirza")
        window._apply()
        app.update_idletasks()

        assert json.loads(captured["values"]) == {"full_name": "Mirza"}
    finally:
        app.destroy()


def test_form_workspace_clear_empties_the_fields(sample_pdf, workspace):
    from src.gui_forms import FormWorkspace
    from src.pdf_forms import create_form_field

    form_pdf = create_form_field(
        sample_pdf, workspace, field_name="note", initial_value="preset"
    ).outputs[0]

    app = _new_app()
    try:
        window = FormWorkspace(app, form_pdf)
        app.update_idletasks()
        assert window.variables["note"].get() == "preset"

        window._clear()

        assert window.collect() == {"note": ""}
    finally:
        app.destroy()


def test_signature_pad_renders_a_trimmed_transparent_png():
    from src.gui_signature import SignaturePad

    app = _new_app()
    try:
        pad = SignaturePad(app)
        pad.strokes = [[(20, 120), (90, 30), (160, 120)]]
        image = pad.render_png()

        assert image.mode == "RGBA"
        assert image.width < 200 and image.height < 150  # trimmed to the ink
        assert image.getbbox() is not None
    finally:
        app.destroy()


def test_signature_pad_refuses_to_save_an_empty_drawing():
    from src.gui_signature import SignaturePad

    app = _new_app()
    saved: list[object] = []
    try:
        pad = SignaturePad(app, on_save=saved.append)
        pad._save()

        assert not saved
        assert "Draw something first" in pad.status.get()
    finally:
        app.destroy()


def test_dropped_files_are_filtered_by_type(sample_pdf, workspace):
    app = _new_app()
    try:
        junk = workspace / "archive.zip"
        junk.write_bytes(b"not supported")

        class FakeEvent:
            data = "{%s} {%s}" % (sample_pdf, junk)

        app._on_drop(FakeEvent())

        assert app.files == [sample_pdf]
    finally:
        app.destroy()
