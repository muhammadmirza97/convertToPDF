# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

**Local PDF Toolbox** — an offline-only Windows desktop app for converting, organizing,
optimizing, editing, and securing PDFs. Nothing is uploaded; no accounts, no cloud APIs,
no telemetry.

Read [projectgoal.md](projectgoal.md) for scope, [plan.md](plan.md) for the phase
roadmap, and [progress.md](progress.md) for current state. Update `plan.md` and
`progress.md` whenever a roadmap item is completed.

## Commands

All commands run from the repo root using the project virtual environment.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt   # install deps
.\scripts\install_shortcut.ps1                                  # create the desktop icon
.\.venv\Scripts\python.exe run_app.py                           # launch the GUI
.\.venv\Scripts\python.exe -m pytest -q                         # run all tests
.\.venv\Scripts\python.exe -m pytest tests/test_pdf_pages.py -q # run one test file
.\.venv\Scripts\python.exe cli.py --list                        # list registered tools
.\.venv\Scripts\python.exe -m compileall src                    # syntax check
.\.venv\Scripts\python.exe assets\make_icon.py                  # regenerate the app icon
```

The desktop shortcut runs `.venv\Scripts\pythonw.exe run_app.py`, so there is no console.
Startup errors must therefore surface as a dialog plus a `logs\app.log` entry — that is what
`run_app.py` is for; keep it working.

The app closes itself after `PDF_TOOLBOX_IDLE_MINUTES` (default 30) of no input. When adding
long-running work, make sure `is_running` is true for its whole duration, or the idle timer
may close the window mid-job.

## Architecture

The GUI is a thin shell. All document processing lives in GUI-free service modules so it
can be reused by the CLI, tests, or a future workflow engine.

```text
src/app.py            CustomTkinter dashboard (category sidebar + dynamic option form)
src/gui_organize.py   thumbnail workspace that builds a page plan
src/gui_forms.py      form workspace that builds field values as JSON
src/gui_signature.py  freehand signature pad
src/tool_registry.py  single source of truth: every tool, its inputs, options, processor
src/converter.py      run_tool() orchestration, batch isolation, progress/log callbacks
src/file_validation.py input, output and dependency validation
src/output_paths.py   safe/no-overwrite output naming, path containment
src/pdf_tools.py      readers, merge, split, page->image, text, markdown, text search
src/pdf_pages.py      rotate, extract, remove, reorder, insert, apply_page_plan
src/pdf_optimize.py   compress, repair
src/pdf_edit.py       watermark, page numbers, crop
src/pdf_annotate.py   highlight, add text, shapes, images
src/pdf_forms.py      read, fill, flatten and create AcroForm fields
src/pdf_redact.py     permanent content removal
src/pdf_sign.py       signature placement
src/pdf_compare.py    text diff report + visual diff PDF
src/pdf_export.py     PDF -> Excel, PDF -> PowerPoint
src/pdf_security.py   protect, unlock, strip metadata
src/ocr_tools.py      Tesseract detection + searchable PDF output
src/thumbnails.py     page thumbnail rendering
src/image_tools.py    image -> PDF
src/text_tools.py     TXT -> PDF
src/html_tools.py     HTML -> PDF
src/office_tools.py   LibreOffice headless conversion (also PDF -> Word, PDF/A)
src/config.py         paths, extension sets, category names, legacy action labels
src/choices.py        case-insensitive option-value matching
src/tool_result.py    ToolOutput: outputs plus a note (e.g. a size saving)
src/logger.py         local file logger (logs/app.log)
cli.py                registry-driven command line
run_app.py            GUI entry point, with startup-failure reporting
scripts/              install_shortcut.ps1, build_exe.ps1
assets/               app icon plus the script that generates it
```

There are exactly two entry points, `run_app.py` and `cli.py`. Do not add a third; new
behaviour belongs in a tool in the registry.

### Adding a new tool

1. Write a pure processing function in the relevant `src/*.py` service module.
   Signature: `fn(input_path, output_dir, **options) -> Path | list[Path] | ToolOutput`.
   For tools that consume all inputs at once (merge, compare), take `list[Path]` and
   register with `batch=False`. Return `ToolOutput` when there is a useful note to report.
2. Register it in `src/tool_registry.py` with a `Tool(...)`: id, label, category,
   accepted extensions, `Option` definitions, and the processor. Set `requires` when it
   needs an external engine, and add the key to `DEPENDENCY_MESSAGES` and
   `DEPENDENCY_LABELS` in `src/file_validation.py`.
3. Add tests in `tests/` covering one success path and one failure path.
4. The GUI and CLI pick the tool up automatically — no GUI code changes needed.

Never add tool-specific branching to `src/app.py` or `src/converter.py`. When a tool needs
an interactive helper, add a generic mechanism instead: the `Tool.workspace` field, or a new
option `kind` the form builder understands (as `KIND_SIGNATURE` does).

Workspaces (`organize`, `form`) are windows that build a value and write it into one of the
tool's options through `_apply_workspace_value()`. To add another, write the window in its own
`src/gui_*.py`, set `workspace="name"` on the tool, add one branch in `_open_workspace()`, and
add the option key to the mapping in `test_workspace_tools_have_the_option_the_workspace_fills`.

A registry test asserts every declared option is a real keyword argument of its processor,
so a typo in an option key fails the suite rather than being silently ignored.

## Hard rules

These are product invariants; tests enforce them.

- **Never modify or delete an input file.** Write new files only.
- **Never overwrite an existing output.** Use `safe_output_path()` /
  `derived_folder()`, which append `_001`, `_002`, ….
- **Never let an output path escape the chosen output folder.**
- **Never send document contents anywhere.** No network calls in processing code.
- **Never log document contents** — filenames, actions, and errors only.
- Raise `ValueError` for expected user errors (bad page range, wrong password) so the GUI
  shows a plain message instead of a stack trace. Reserve `RuntimeError` for missing
  external dependencies.
- Clean up temporary files on success *and* failure (`tempfile.TemporaryDirectory`).
- Keep every external dependency optional and detected at runtime (LibreOffice, Tesseract),
  with the tool clearly disabled when absent.
- Never overstate what a tool does. Redaction, signing and the PDF-to-Office conversions
  each carry an honest limitation in their hint text, the README and
  `docs/KNOWN_LIMITATIONS.md`; keep those in step with the code.
- When nothing matched (no text found, no table detected), raise `ValueError` and write no
  output rather than producing an unchanged file that looks like success.

## Conventions

- Python 3.12+, `from __future__ import annotations` at the top of every module.
- Type hints on all public functions; `Path` over `str` internally.
- Options are keyword-only arguments with beginner-safe defaults.
- Error messages name the affected file and say what the user should do next.
- Tests use the `workspace` fixture (`tests/conftest.py`), which is pytest's `tmp_path`, and
  build their own PDF/image fixtures. Never write test output into the project folder, and do
  not commit binary test assets.
- `pikepdf` for encryption/repair, `pypdf` for page structure, `PyMuPDF` (`fitz`) for
  rendering and drawing, `Pillow` for images, `reportlab` for text layout.
