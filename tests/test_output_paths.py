from __future__ import annotations

from src.output_paths import derived_folder, safe_output_path, sanitize_base_name


def test_safe_output_path_does_not_overwrite(workspace):
    first = safe_output_path(workspace, "report", ".pdf")
    first.write_text("existing", encoding="utf-8")

    second = safe_output_path(workspace, "report", ".pdf")

    assert second.name == "report_001.pdf"
    assert second != first


def test_safe_output_path_adds_extension_dot(workspace):
    output = safe_output_path(workspace, "invoice.txt", "pdf")

    assert output.name == "invoice.pdf"


def test_safe_output_path_sanitizes_windows_unsafe_names(workspace):
    output = safe_output_path(workspace, '..\\bad:name*with?chars', ".pdf")

    assert output.parent == workspace.resolve()
    assert output.name == "bad_name_with_chars.pdf"


def test_safe_output_path_handles_reserved_windows_names(workspace):
    output = safe_output_path(workspace, "CON", ".pdf")

    assert output.name == "CON_file.pdf"


def test_derived_folder_stays_inside_output_folder(workspace):
    folder = derived_folder(workspace, "../pages")

    assert folder.parent == workspace.resolve()
    assert folder.name == "pages"


def test_sanitize_base_name_falls_back_for_blank_names():
    assert sanitize_base_name("...") == "converted"
