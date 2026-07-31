"""Orchestration tests: batching, failure isolation, options and output safety."""

from __future__ import annotations

import pytest

from src.converter import run_tool
from src.tool_registry import get_tool
from tests.conftest import build_image, build_pdf


def test_run_tool_isolates_a_single_bad_file(workspace):
    good = build_pdf(workspace / "good.pdf", pages=2)
    broken = workspace / "broken.pdf"
    broken.write_bytes(b"not really a pdf")

    summary = run_tool("rotate_pdf", [good, broken], workspace)

    assert summary.succeeded == 1
    assert summary.failed == 1
    assert not summary.ok
    assert "broken.pdf" in summary.results[1].message


def test_run_tool_passes_options_through(sample_pdf, workspace):
    summary = run_tool("extract_pages", [sample_pdf], workspace, {"pages": "2"})

    assert summary.ok
    assert len(summary.outputs) == 1


def test_run_tool_reports_bad_option_values_per_file(sample_pdf, workspace):
    summary = run_tool("rotate_pdf", [sample_pdf], workspace, {"pages": "nonsense"})

    assert summary.failed == 1
    assert "numbers" in summary.results[0].message


def test_run_tool_rejects_the_wrong_file_type_before_starting(workspace):
    text = workspace / "notes.txt"
    text.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="PDF"):
        run_tool("rotate_pdf", [text], workspace)


def test_run_tool_rejects_a_missing_file(workspace):
    with pytest.raises(ValueError, match="File not found"):
        run_tool("rotate_pdf", [workspace / "ghost.pdf"], workspace)


def test_run_tool_requires_at_least_one_file(workspace):
    with pytest.raises(ValueError, match="at least one file"):
        run_tool("rotate_pdf", [], workspace)


def test_non_batch_tool_receives_every_file_at_once(workspace):
    first = build_pdf(workspace / "first.pdf", pages=1)
    second = build_pdf(workspace / "second.pdf", pages=1)

    summary = run_tool("merge_pdfs", [first, second], workspace)

    assert summary.succeeded == 1
    assert len(summary.results) == 1


def test_progress_and_log_callbacks_fire(workspace):
    first = build_pdf(workspace / "first.pdf", pages=1)
    second = build_pdf(workspace / "second.pdf", pages=1)
    progress: list[tuple[int, int, str]] = []
    messages: list[str] = []

    run_tool(
        "rotate_pdf",
        [first, second],
        workspace,
        progress_callback=lambda done, total, message: progress.append((done, total, message)),
        log_callback=messages.append,
    )

    assert progress[-1][0] == progress[-1][1] == 2
    assert len(messages) == 2


def test_outputs_never_overwrite_earlier_runs(sample_pdf, workspace):
    first = run_tool("rotate_pdf", [sample_pdf], workspace).outputs[0]
    second = run_tool("rotate_pdf", [sample_pdf], workspace).outputs[0]

    assert first != second
    assert second.name == "sample_rotated_001.pdf"
    assert first.exists()


def test_inputs_are_never_modified(workspace):
    source = build_pdf(workspace / "source.pdf", pages=2)
    before = source.read_bytes()

    for tool_id, options in [
        ("rotate_pdf", {}),
        ("remove_pages", {"pages": "1"}),
        ("watermark_pdf", {"text": "DRAFT"}),
        ("compress_pdf", {}),
        ("strip_metadata", {}),
        ("protect_pdf", {"new_password": "secret123"}),
    ]:
        summary = run_tool(tool_id, [source], workspace, options)
        assert summary.ok, summary.results[0].message

    assert source.read_bytes() == before


def test_outputs_stay_inside_the_chosen_folder(workspace):
    source = build_pdf(workspace / "source.pdf", pages=1)
    output_dir = workspace / "results"

    summary = run_tool("rotate_pdf", [source], output_dir)

    assert summary.outputs[0].parent == output_dir.resolve()


def test_auto_tool_handles_a_mixed_selection(workspace):
    image = build_image(workspace / "photo.png")
    text = workspace / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    html = workspace / "page.html"
    html.write_text("<p>hi</p>", encoding="utf-8")

    summary = run_tool("auto_to_pdf", [image, text, html], workspace)

    assert summary.succeeded == 3
    assert all(path.suffix == ".pdf" for path in summary.outputs)


def test_auto_tool_explains_pdf_input(workspace):
    text = workspace / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    pdf = build_pdf(workspace / "already.pdf", pages=1)

    summary = run_tool("auto_to_pdf", [text, pdf], workspace)

    assert summary.succeeded == 1
    assert "Choose a PDF action" in summary.results[1].message


def test_office_tool_is_blocked_without_libreoffice(monkeypatch, workspace):
    monkeypatch.setattr("src.converter.find_libreoffice", lambda: None)
    docx = workspace / "letter.docx"
    docx.write_bytes(b"not a real docx")

    with pytest.raises(ValueError, match="LibreOffice"):
        run_tool("office_to_pdf", [docx], workspace)


def test_every_tool_label_and_id_resolve_to_the_same_tool():
    for tool_id in ("rotate_pdf", "compress_pdf", "protect_pdf"):
        tool = get_tool(tool_id)
        assert get_tool(tool.label) is tool
