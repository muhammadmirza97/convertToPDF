from __future__ import annotations

import cli
from tests.conftest import build_pdf


def test_list_prints_every_category(capsys):
    exit_code = cli.main(["--list"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Organize" in output
    assert "rotate_pdf" in output


def test_help_tool_shows_options(capsys):
    exit_code = cli.main(["--help-tool", "pdf_to_images"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "image_format" in output
    assert "png | jpg" in output


def test_help_tool_rejects_unknown_tool(capsys):
    exit_code = cli.main(["--help-tool", "teleport_pdf"])

    assert exit_code == 2
    assert "Unknown tool" in capsys.readouterr().out


def test_run_a_tool_with_settings(workspace, capsys):
    source = build_pdf(workspace / "source.pdf", pages=3)

    exit_code = cli.main(["extract_pages", str(source), "-o", str(workspace), "--set", "pages=1-2"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Created:" in output
    assert (workspace / "source_extracted.pdf").exists()


def test_validation_failure_returns_exit_code_two(workspace, capsys):
    text = workspace / "notes.txt"
    text.write_text("hello", encoding="utf-8")

    exit_code = cli.main(["rotate_pdf", str(text), "-o", str(workspace)])

    assert exit_code == 2
    assert "Could not start" in capsys.readouterr().out


def test_per_file_failure_returns_exit_code_one(workspace, capsys):
    broken = workspace / "broken.pdf"
    broken.write_bytes(b"not a pdf")

    exit_code = cli.main(["rotate_pdf", str(broken), "-o", str(workspace)])

    assert exit_code == 1


def test_unknown_tool_is_reported(capsys):
    exit_code = cli.main(["teleport_pdf", "file.pdf"])

    assert exit_code == 2
    assert "Unknown tool" in capsys.readouterr().out
