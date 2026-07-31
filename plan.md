# Project Plan

## Planning Basis

The current codebase is a working local PDF converter and processing foundation. The next goal is to evolve it into a broader local PDF toolbox inspired by the task coverage and ease of use of iLovePDF.

The plan prioritizes reliable local operations before advanced editing or AI features.

## Phase 0 — Stabilize the Existing Foundation — DONE (2026-07-31)

**Goal:** Establish a trustworthy baseline before adding more tools.

- [x] Fix cross-platform filename sanitization so Windows-style paths are handled consistently on Windows and POSIX test environments.
- [x] Re-run all automated tests on Windows.
- [x] Test real DOC, DOCX, PPT, PPTX, XLS, and XLSX conversion with LibreOffice installed. Verified DOCX, XLSX, PPTX end to end; see `docs/QA_REPORT.md`.
- [ ] Add continuous integration for at least Windows and Linux core tests.
- [x] Pin or constrain dependency versions for reproducible installations.
- [x] Add test coverage for corrupted PDFs, zero-page PDFs, and encrypted PDFs. Very large files and interrupted operations are still untested.
- [ ] Commit the current reviewed snapshot as a clean baseline.

**Exit criteria:** Met for the Windows environment. CI is still outstanding.

## Phase 1 — Restructure the Product Around Tools — DONE (2026-07-31)

**Goal:** Make the application easy to extend from eight actions to a full toolbox.

- [x] Replace the single action dropdown with a categorized tool dashboard.
- [x] Create categories: Convert to PDF, Convert from PDF, Organize, Optimize, Edit, Security. Workflows is deferred to Phase 6.
- [x] Introduce a tool registry containing each tool's name, accepted inputs, options, processor, and output behavior (`src/tool_registry.py`).
- [x] Create a shared job model for progress, results, warnings, and errors (`run_tool`, `ConversionSummary`). Cancellation is not implemented.
- [x] Run long operations outside the GUI thread.
- [ ] Add drag-and-drop file input. Needs a third-party Tk extension; deferred.
- [x] Add an output summary with a button to open the output folder.
- [x] Preserve processing services independently from the interface.
- [x] Add a command-line interface driven by the same registry (`cli.py`). Moved forward from Phase 6.

**Exit criteria:** Met. A new tool needs one processing function plus one registry entry; no GUI or CLI changes.

## Phase 2 — Essential Organize Tools — DONE (2026-07-31)

**Goal:** Cover the most common daily PDF page operations.

1. [x] Rotate pages
2. [x] Extract selected pages
3. [x] Remove selected pages
4. [x] Reorder pages
5. [ ] Combine reordering, removal, rotation, and insertion into one visual Organize workspace. Each operation ships as its own tool; the combined workspace needs thumbnails.

Implementation requirements:

- [ ] Generate page thumbnails locally.
- [x] Support page-range syntax. Visual page selection still needs thumbnails.
- [x] Preserve page dimensions, orientation, and document metadata. Bookmarks are not always preserved.
- [ ] Add undo/reset before export. Not needed yet: every tool writes a new file and never touches the input.
- [x] Add unit and integration tests for every page operation.

**Exit criteria:** Partially met. Users can rearrange a PDF by typing page orders and export a new file without changing the original; the thumbnail view is outstanding.

## Phase 3 — Optimization and Presentation Tools — DONE (2026-07-31)

**Goal:** Deliver high-value tools that are practical to implement locally.

- [x] Compress PDF with three understandable presets: low compression, balanced, and maximum compression.
- [x] Add text and image watermarks with opacity, angle, scale, colour, and page-range options.
- [x] Add page numbers with position, starting number, format, margins, and page-range options.
- [x] Crop pages using margins. The visual crop rectangle needs a page preview.
- [x] Expand PDF-to-image export with JPG, PNG, DPI, quality, grayscale, and selected-page controls.
- [x] Expand image-to-PDF with page size, fit mode, orientation, margins, and image ordering.

**Exit criteria:** Met, except that settings cannot be previewed before running.

Potential local dependencies should be evaluated rather than bundled blindly. PyMuPDF can cover many operations; Ghostscript may improve compression; all licensing and redistribution constraints must be reviewed.

**Exit criteria:** Compression and document presentation tools produce predictable outputs with previewable settings.

## Phase 4 — Security Tools — DONE (2026-07-31)

**Goal:** Add safe local protection and privacy operations.

- [x] Protect PDFs with user-supplied passwords and modern encryption (AES-256, pikepdf revision 6).
- [x] Unlock PDFs only when the user provides a valid password.
- [x] Add password entry to existing encrypted-PDF workflows. Every PDF tool takes an optional password.
- [x] Add true redaction that permanently removes selected content, not merely covers it visually. Text search, millimetre areas, or all images.
- [x] Metadata removal. Metadata inspection exists as `read_metadata()` but has no GUI screen yet.
- [x] Add a local signature image or freehand signature placement tool. Both: browse to an image, or draw one in the signature pad.
- [x] Define secure handling rules for temporary files and sensitive logs. See `docs/SECURITY_REVIEW.md`.

pikepdf (a qpdf binding) was chosen for encryption, decryption and repair, so a separate qpdf install is not required.

**Exit criteria:** Met. Tests confirm a protected PDF cannot be read without its password, and that redacted text is absent from the output's extracted text.

## Phase 5 — OCR, Repair, and Advanced Conversion — DONE (2026-07-31)

**Goal:** Support scanned and structurally difficult documents.

- [x] Integrate local OCR using Tesseract, through PyMuPDF rather than OCRmyPDF, which avoids a Ghostscript dependency.
- [x] Create searchable PDFs while preserving the scanned page image.
- [x] Add language-pack selection and clear installation guidance. Installed codes are detected, listed in the header, and validated before use.
- [x] Add PDF repair through a proven local engine (pikepdf, with a PyMuPDF fallback).
- [x] Add PDF/A conversion. Validation is limited to checking the PDF/A identification metadata; a formal validator such as veraPDF is still recommended.
- [x] Improve TXT-to-PDF Unicode and font support. A local TrueType font is registered when available; CJK and Arabic still need a bundled font.
- [x] Add HTML-to-PDF using a maintained local rendering engine (PyMuPDF Story). Simple documents only.
- [x] Add PDF-to-Markdown as a best-effort text conversion.
- [x] PDF-to-Word through the LibreOffice Writer import filter; PDF-to-Excel through table detection plus openpyxl; PDF-to-PowerPoint through python-pptx with one page image per slide.

PDF-to-Office conversion is presented as best-effort in the tool hints, the README and the limitations document.

**Exit criteria:** Met. Scanned PDFs become searchable locally, and every advanced conversion states its limitations.

## Phase 6 — Editing, Forms, Compare, and Workflows — PARTIALLY DONE (2026-07-31)

**Goal:** Add advanced capabilities after the core toolbox is stable.

- [x] Add annotations: text, highlight, shapes, drawing, and image placement. Positions are typed in millimetres; click-on-page placement is still missing.
- [x] Add basic PDF form filling, with a field workspace and optional flattening. AcroForm only; XFA is not supported.
- [x] Evaluate form-field creation. Delivered for text boxes, checkboxes and dropdowns; no validation rules, calculations or radio groups.
- [x] Add side-by-side visual and text comparison. Markdown diff report plus a visual PDF marking changed pages.
- [ ] Build a workflow editor for chaining tools.
- [ ] Save workflow definitions as local JSON.
- [ ] Add batch folders and watched-folder processing as an optional feature.
- [x] Add a command-line interface using the same tool registry. Delivered early in Phase 1.

**Exit criteria:** Not met. Editing, comparison and forms ship; reusable workflows and watched folders remain. Workflows are low priority for single-user personal use.

## Phase 7 — Packaging and Release Quality

**Goal:** Make installation and daily use dependable for non-developers.

- [ ] Produce a signed Windows installer or portable executable.
- [x] Provide a one-click desktop icon that launches the app with no console window (`scripts\install_shortcut.ps1`).
- [x] Report startup failures in a dialog and in the log, since the icon has no console.
- [x] Close the app automatically after 30 minutes of inactivity, with a countdown warning and a running-job exemption.
- [ ] Decide which dependencies can be bundled and which require separate installation.
- [ ] Add first-run dependency checks.
- [ ] Add application versioning and migration handling for saved settings.
- [ ] Add crash reporting that is local-only by default.
- [ ] Test on a clean Windows virtual machine.
- [ ] Test high-DPI displays and common screen sizes.
- [ ] Add accessibility checks for keyboard navigation, labels, focus, and contrast.
- [ ] Publish a user guide, privacy statement, dependency notice, and third-party licenses.

**Exit criteria:** A new user can install, open, and complete a supported task without Python or developer tooling.

## Completed Sprints (2026-07-31)

### Version 2 — Essential toolbox

1. [x] Fix the filename sanitization test failure found during the July 31, 2026 Linux audit.
2. [x] Verify all existing tests on Windows.
3. [x] Verify Word, PowerPoint, and Excel conversion with LibreOffice installed.
4. [x] Add Rotate PDF as the first new tool, with tests and documentation.
5. [x] Build the tool registry, then deliver the rest of the Version 2 toolbox on top of it.

### Version 3 — Feature-parity MVP

1. [x] Page thumbnails, plus the visual Organize workspace and page plans built on them.
2. [x] True redaction using PyMuPDF `add_redact_annot` and `apply_redactions`.
3. [x] OCR through Tesseract, with language detection and installation guidance.
4. [x] Sign PDF, including a freehand signature pad.
5. [x] Compare two PDFs, text and visual.
6. [x] PDF to Word, Excel, PowerPoint and PDF/A.
7. [x] Annotation tools: highlight, add text, shapes, images.
8. [x] Drag-and-drop file input.
9. [x] Form filling, field creation, field listing, and a form workspace.
10. [x] Extract embedded images, fixed-size splitting, tiled watermarks.

## Near-Term Sprint

The next development sprint should contain only these items:

1. [ ] Commit the Version 3.1 snapshot as a clean baseline.
2. [ ] Add click-on-the-page placement and a preview for the editing, crop, redaction and form-field tools. This is now the largest remaining usability gap.
3. [ ] Verify the PyInstaller build on a clean Windows machine, including the `tkinterdnd2` Tcl files.
4. [ ] Add cancellation for long operations, starting with OCR.
5. [ ] Add GitHub Actions CI running the core suite on Windows and Linux.
6. [ ] Validate PDF/A output with veraPDF and report the result honestly.

## Recommended Technical Direction

- **GUI:** Continue with CustomTkinter for the near term; reconsider Qt only if thumbnail-heavy editing becomes difficult.
- **Core PDF operations:** PyMuPDF and pypdf. Chosen and in use.
- **Images:** Pillow. `img2pdf` was dropped; PyMuPDF handles page layout.
- **Office to PDF:** LibreOffice headless mode. In use and verified.
- **OCR:** Tesseract driven through PyMuPDF's `pdfocr_tobytes`. Chosen over OCRmyPDF because it avoids a Ghostscript dependency and needs no extra Python packages.
- **Compression/rendering:** PyMuPDF `rewrite_images` plus garbage collection. Measured 52-98% reductions on image-heavy PDFs, so Ghostscript is not needed yet.
- **Encryption/repair:** pikepdf (qpdf bindings), plus `cryptography` so pypdf can also read AES-256 files.
- **PDF to Office:** LibreOffice for Word and PDF/A; openpyxl and python-pptx for Excel and PowerPoint, which keeps those two tools working without LibreOffice.
- **Drag and drop:** tkinterdnd2, imported optionally so a missing install only disables the feature.
- **Testing:** pytest with generated fixtures and golden-file checks where appropriate.
- **Packaging:** PyInstaller initially, followed by a Windows installer once dependency strategy is stable.

## Quality Gates for Every Phase

- [ ] No original file is modified.
- [ ] No existing output is overwritten silently.
- [ ] All document processing remains local.
- [ ] Expected user errors do not produce raw stack traces in the GUI.
- [ ] Temporary files are cleaned after success and failure.
- [ ] New behavior has automated tests.
- [ ] Documentation and known limitations are updated.
- [ ] Third-party licensing is reviewed before distribution.
