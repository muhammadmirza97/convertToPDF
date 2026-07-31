# Project Progress

**Status date:** 2026-07-31
**Current stage:** Version 3.2 — one-click launch and automatic shutdown — delivered. 40 tools
across six categories, all offline, no account or sign-up anywhere, started from a desktop
icon. Remaining gaps are interaction polish (click-on-page placement and previews), packaging
and CI.

## Current Product State

A local-only Windows desktop toolbox with a categorized dashboard, a registry of 40 tools,
a thumbnail workspace for page organizing, a form-filling workspace, a signature pad,
drag-and-drop input, a matching command line, GUI-free service modules, safe output
handling, batch failure isolation, logging, and 261 automated tests.

Two optional local engines are detected at startup and reported in the header: LibreOffice
and Tesseract. Tools that need a missing engine are disabled, naming the engine required.

## Implemented Features

### Convert to PDF (5 tools)

- [x] PNG / JPG / JPEG to PDF, one combined PDF or one per image
- [x] Image page size, orientation, fit mode and margin options
- [x] TXT to PDF, with font size, page size, orientation and margin
- [x] HTML to PDF (local files, simple documents)
- [x] DOC/DOCX, PPT/PPTX, XLS/XLSX to PDF through LibreOffice — verified with real files
- [x] Auto convert, which routes a mixed selection to the right converter per file

### Convert from PDF (8 tools)

- [x] PDF pages to PNG or JPG, with DPI, JPG quality, grayscale and page selection
- [x] Extract embedded images in their original format, with a minimum-size filter
- [x] Text extraction with page selection
- [x] Markdown extraction with heading guessing
- [x] PDF to Word (.docx) through the LibreOffice Writer import filter
- [x] PDF to Excel (.xlsx): detected tables, or text lines, as worksheets
- [x] PDF to PowerPoint (.pptx): one slide per page, page text in the speaker notes
- [x] PDF to PDF/A-1b, 2b or 3b

### Organize (9 tools)

- [x] Merge multiple PDFs
- [x] Split every page, selected ranges such as `1-3,5`, or fixed chunks of N pages
- [x] Rotate selected pages
- [x] Extract selected pages, as one PDF or one PDF per page
- [x] Remove selected pages
- [x] Reorder pages by typing a new order
- [x] Insert every page of another PDF at a chosen position
- [x] Organize pages visually: thumbnail workspace producing a page plan
- [x] Compare two PDFs: Markdown text diff plus a side-by-side visual PDF

### Optimize (3 tools)

- [x] Compress PDF with Low / Balanced / Maximum presets, reporting the size saved
- [x] Never write a compressed file larger than the original
- [x] Repair PDF through pikepdf, falling back to PyMuPDF
- [x] OCR PDF: Tesseract, keeps the page image, adds an invisible text layer, validates the
      requested language against the installed packs

### Edit (10 tools)

- [x] Text watermark with opacity, angle, size, colour, tiled or centred, and page range
- [x] Image watermark with opacity and scale
- [x] Page numbers with position, format, start number, size, colour and margin
- [x] Crop pages by millimetre margins
- [x] Highlight, underline, strike out or squiggly-mark found text
- [x] Add text at any position, with size and colour
- [x] Add rectangle, ellipse, line or arrow, optionally filled
- [x] Add an image at a chosen position and width
- [x] List a form's fillable fields to editable JSON
- [x] Fill an existing PDF form, with optional flattening to lock the values
- [x] Create text box, checkbox and dropdown form fields

### Security (5 tools)

- [x] Protect with an AES-256 password, with printing and copying permissions
- [x] Unlock a PDF when the correct password is supplied
- [x] Remove document information and XMP metadata
- [x] Redact PDF: permanently removes text, millimetre areas, or all images
- [x] Sign PDF: place a scanned or hand-drawn signature, with optional name and date caption
- [x] Password entry on every PDF tool, so protected files can be processed directly

### Application Foundation

- [x] Tool registry as the single source of truth (`src/tool_registry.py`)
- [x] Categorized dashboard GUI with a per-tool option form built from the registry
- [x] Thumbnail Organize workspace: select, rotate, move, delete, reset, export a plan
- [x] Form workspace: every field with the right editor for its type, read-only respected
- [x] Signature pad: draw with the mouse, choose ink and thickness, saved as a trimmed
      transparent PNG under `output/signatures/`
- [x] Drag-and-drop file input, rejecting and reporting unsupported files
- [x] Registry-driven validation, including per-tool dependency messages
- [x] Generic `Tool.workspace` field and `signature` option kind, so interactive helpers
      need no tool-specific GUI code
- [x] `run_tool()` orchestration with progress and log callbacks
- [x] Long operations run off the GUI thread
- [x] Per-file batch failure isolation
- [x] Open output folder button
- [x] Registry-driven CLI with `--list`, `--help-tool` and `--set key=value`
- [x] Two entry points only: `run_app.py` for the GUI and `cli.py` for the command line
- [x] Local log file; no document contents and no passwords logged
- [x] No cloud APIs, uploads, telemetry or paid services
- [x] Original files are never modified
- [x] Existing output files are never overwritten
- [x] Output names sanitized, deterministic on Windows and POSIX
- [x] Output-path containment checks
- [x] Temporary files cleaned on success and failure
- [x] Optional engines detected at runtime, with tools disabled and labelled when absent
- [x] Constrained dependency versions
- [x] Desktop icon created by `scripts\install_shortcut.ps1`, launching through `pythonw.exe`
      with no console window; window and taskbar use the same icon
- [x] Startup failures reported in a dialog and in `logs/app.log`, since the shortcut has no
      console to print to
- [x] Closes itself after 30 minutes of no input, with a one-minute countdown warning and a
      Keep working button; a running job always counts as activity
- [x] Idle timeout configurable through `PDF_TOOLBOX_IDLE_MINUTES`, `0` to disable
- [x] Docker configuration for core tests
- [x] PyInstaller build script, now with the icon and bundled assets

## Architecture Completed

```text
app.py / gui_organize.py / gui_forms.py / gui_signature.py / cli.py
        |
        v
converter.run_tool()  ->  tool_registry.Tool.processor
        |                          |
 file_validation           service modules:
 output_paths              pdf_tools, pdf_pages, pdf_optimize, pdf_edit, pdf_annotate,
 logger                    pdf_forms, pdf_redact, pdf_sign, pdf_compare, pdf_export,
                           pdf_security, ocr_tools, thumbnails, image_tools, text_tools,
                           html_tools, office_tools
```

No interface code contains tool-specific branching. A registry test asserts every option is
a real argument of its processor, so option typos fail the suite.

## Test and Review Status

Windows run on 2026-07-31:

```text
273 passed, 2 skipped in 25.80s
compileall succeeded
No broken requirements found
GUI dashboard, Organize workspace, form workspace, signature pad and drop filtering all pass
Desktop shortcut launches the app through pythonw.exe with no console
Idle shutdown verified end to end: closed itself after 9.2s with a 7s timeout, exit code 0
LibreOffice detected at C:\Program Files\LibreOffice\program\soffice.COM
Tesseract detected at C:\Program Files\Tesseract-OCR\tesseract.exe (languages: eng, osd)
```

Manual verification of OCR on a pixel-only scan, redaction actually removing content, all
four PDF-to-Office conversions, compression ratios, and the protect/unlock round trip is
recorded in `docs/QA_REPORT.md`.

## Working but Not Fully Verified

- [~] PyInstaller Windows executable on a clean machine, including bundling the
      `tkinterdnd2` Tcl files
- [~] Docker test image after the Version 3 changes
- [~] OCR in languages other than English; only the `eng` pack is installed here
- [~] PDF/A output against a formal validator such as veraPDF
- [~] Very large documents (hundreds of megabytes)
- [~] Continuous integration on Linux

## Not Yet Implemented

- [ ] Click-on-the-page placement and previews for editing, crop, redaction and form fields
- [ ] Dragging thumbnails to reorder (Move left and Move right do it today)
- [ ] XFA form support (AcroForm only)
- [ ] Cancel a running operation
- [ ] Metadata inspection screen (the function exists, the GUI does not)
- [ ] Scan capture from a camera or scanner device
- [ ] Reusable multi-step workflows saved as local JSON — low priority for personal use
- [ ] Watched-folder batch processing
- [ ] Windows installer and first-run dependency check (the desktop icon covers day-to-day
      launching, but it still needs the project folder and its virtual environment in place)
- [ ] Continuous integration

Deliberately out of scope, because the product is local-first and single-user: accounts,
sign-up, paid tiers, cloud storage import, share links, server-side task history, mobile
apps, and fetching a web address for HTML to PDF.

## Known Limitations

See `docs/KNOWN_LIMITATIONS.md` for the full list. The headline ones:

- Sign PDF places a visible signature only. It is not a certified digital signature.
- Redaction removes what it matches, but text drawn as an image, text split across lines,
  metadata and attachments are not caught by a text search. Review before sharing.
- PDF to Word, Excel, PowerPoint and Markdown are best-effort reconstructions.
- OCR quality depends on the scan; low-DPI or skewed scans read poorly.
- Crop hides content rather than deleting it; use Redact PDF for removal.
- HTML to PDF handles simple documents only; it is not a browser engine.
- TXT to PDF cannot render CJK or Arabic without a suitable font.
- Comparison is positional, so inserting an early page marks every later page as changed.
- Forms support AcroForm only; XFA forms cannot be read. Flattening cannot be undone.

## Immediate Next Actions

1. [ ] Commit the Version 3.1 snapshot as a clean baseline.
2. [ ] Add click-on-the-page placement and previews for editing, crop, redaction and forms.
3. [ ] Verify the PyInstaller build on a clean Windows machine.
4. [ ] Add cancellation for long operations, starting with OCR.
5. [ ] Add CI for Windows and Linux core tests.
6. [ ] Validate PDF/A output with veraPDF.

## Overall Assessment

### Foundation

**Strong.** The registry carried 17 new tools across this stage with no interface rewrites,
and all three interactive helpers were added through generic mechanisms rather than special
cases. The second workspace needed no new GUI plumbing at all.

### Feature Parity

**Met for tool coverage.** Every tool a mainstream online PDF service offers now has a local
equivalent, apart from camera scanning and URL-based HTML conversion, both of which are out
of scope on purpose. A registry test pins the expected tool list so it cannot silently
regress.

**Not met for interaction polish.** Editing and form-field positions are typed in millimetres
rather than clicked on a page preview, page reordering uses buttons rather than dragging, and
there are no live previews. That is the main daily-use difference a user would still notice,
and it is the top item in the next sprint.

### Release Readiness

**Usable now for personal use.** Set up once with `pip install -r requirements.txt` and
`scripts\install_shortcut.ps1`, then it opens from a desktop icon like any other app and closes itself
when left idle. A packaged installer, CI, and a clean-machine test remain before it could be
handed to someone who does not have Python at all.
