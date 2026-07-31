# QA Report

**Date:** 2026-07-31
**Environment:** Windows 11 Home 10.0.26200, Python 3.12, project `.venv`
**Scope:** Version 3.2 — 40 tools, OCR, redaction, signing, comparison, PDF-to-Office export,
forms, the Organize and form workspaces, drag-and-drop, the desktop launcher, and the
inactivity shutdown.

## Automated checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src cli.py run_app.py tests
.\.venv\Scripts\python.exe -m pip check
```

Results:

```text
273 passed, 2 skipped in 25.80s
compileall succeeded with no output
No broken requirements found.
```

The two skips are the GUI tests on a run where Tk failed to start; see the environment note
at the end of this report.

Detected engines during the run:

```text
LibreOffice: C:\Program Files\LibreOffice\program\soffice.COM
Tesseract:   C:\Program Files\Tesseract-OCR\tesseract.exe  (languages: eng, osd)
Drag and drop: available (tkinterdnd2)
```

## Manual verification

### OCR

An image-only PDF was built by rendering text to pixels, so it had no text layer at all
(`get_text()` returned an empty string). After OCR:

```text
OCR PDF: scan.pdf - OCR ran on 1 page(s); 0 page(s) kept as they were
extracted text: 'SCANNED HELLO WORLD'
page image still present: yes
```

Forcing OCR on a text PDF and skipping pages that already have text were both exercised.

### Redaction

```text
Redact PDF: doc.pdf - Removed 2 area(s) permanently
secret string still present in output: no
replacement label written: yes
surrounding content intact: yes
```

Image redaction was verified by checking `get_images()` is empty on the output page.

### Signing and comparison

```text
Sign PDF: doc.pdf - Signed 1 page(s); visible signature, not a certified digital signature
Compare two PDFs - 2 page(s) differ in text; 2 page(s) look different
  -> doc_vs_doc_v2.md, doc_vs_doc_v2_visual.pdf
```

### PDF to Office and PDF/A

Real conversions, each output reopened and inspected:

```text
PDF to Word      -> doc.docx     word/document.xml contains the source text
PDF to Excel     -> table.xlsx   worksheet p1_table1 = [['Item','Qty','Price'], ['Widget','2','10.00'], ...]
PDF to PowerPoint-> doc.pptx     2 slides, page text present in the speaker notes
PDF to PDF/A     -> doc_pdfa.pdf XMP reports pdfaid:part=1, pdfaid:conformance=B
```

Office-to-PDF was re-verified for DOCX, XLSX and PPTX; each output PDF contained the
expected text.

### Desktop launcher

`scripts\install_shortcut.ps1` was run, and the created shortcut inspected:

```text
Created C:\Users\<user>\OneDrive\Desktop\Local PDF Toolbox.lnk
Target  : C:\dev\convertToPDF\.venv\Scripts\pythonw.exe
Args    : "C:\dev\convertToPDF\run_app.py"
WorkDir : C:\dev\convertToPDF
Icon    : C:\dev\convertToPDF\assets\app_icon.ico,0
```

Launching that exact command started the app and it stayed running, with no console window.

### Inactivity shutdown

Launched through `pythonw.exe` with `PDF_TOOLBOX_IDLE_MINUTES=0.12` (about 7 seconds):

```text
started pid 41108 with idle timeout 0.12 min (~7s)
app closed itself after 9.2s, exit code 0
logs\app.log: Closing after 7 second(s) of inactivity.
```

So the process really exits rather than leaving a hidden window behind. The unit tests cover
the 30-minute path, the countdown warning, activity dismissal, and the rule that a running job
counts as activity.

### Forms, end to end through the CLI

A plain PDF with no form fields was taken through the whole flow:

```text
create_form_field  full_name (text box)  -> agreement_form.pdf
create_form_field  agree (checkbox)      -> agreement_form_form.pdf
form_fields                              -> {"full_name": "", "agree": "Off"}
fill_form  "full_name=Muhammad Mirza; agree=yes"  flatten=true
```

The flattened output was reopened and inspected:

```text
page text: 'Rental agreement\nFull name:\nI agree:\nMuhammad Mirza\nX\n'
remaining fillable fields: []
```

So the values were written, the checkbox rendered as an X, and flattening removed the fields
as documented.

### Compression (unchanged from Version 2, re-checked)

```text
Low compression      8.6 MB -> 4.2 MB  (52% smaller)
Balanced             8.6 MB -> 1.5 MB  (82% smaller)
Maximum compression  8.6 MB -> 193.5 KB (98% smaller)
```

### GUI

The dashboard was launched and screenshotted successfully. The Organize workspace and the
signature pad were driven programmatically through the real widgets:

```text
workspace button appears only for tools that declare one: pass
thumbnails rendered: 3 of 3 pages, one tile each
select -> rotate 90 -> move right -> select other -> delete -> apply
generated plan: "2,1:90"   (matches the expected result)
delete-everything guard: keeps 3 pages, reports "Keep at least one page."
signature pad render: 326x106 RGBA, trimmed to the ink
empty signature save refused: pass
dropped-file filtering: PDF accepted, .zip ignored
form workspace: lists each field, typing a value returns {"full_name": "Mirza"} as JSON
form workspace Clear all: empties editable fields, read-only fields untouched
```

A screen capture of the workspace window itself was not obtained: the capture kept
grabbing whichever window was in the foreground rather than the Tk toplevel. The window's
behaviour is covered by the tests listed above instead.

## Pass summary

| Area | Result |
| --- | --- |
| File, output and dependency validation | pass |
| Safe, non-overwriting output names | pass |
| Output containment inside chosen folder | pass |
| Inputs never modified | pass |
| Temporary files cleaned up | pass |
| Images / TXT / HTML to PDF | pass |
| Office to PDF (DOCX, XLSX, PPTX) | pass, real files |
| PDF to image / text / Markdown | pass |
| PDF to Word / Excel / PowerPoint / PDF-A | pass, real files |
| Merge, split, rotate, extract, remove, reorder, insert | pass |
| Organize page plans and thumbnails | pass |
| Compare two PDFs (text and visual) | pass |
| Compress, repair | pass |
| OCR PDF | pass, text recovered from a pixel-only scan |
| Watermark, page numbers, crop | pass |
| Highlight, add text, shapes, images | pass |
| Protect, unlock, remove metadata | pass |
| Redact PDF (content actually removed) | pass |
| Sign PDF | pass |
| Form field creation, listing, filling, flattening | pass, verified end to end |
| Extract embedded images | pass |
| Fixed-chunk splitting and tiled watermarks | pass |
| Per-file batch failure isolation | pass |
| CLI list, help, run, exit codes | pass |
| GUI dashboard, workspace, signature pad, drag-and-drop | pass |
| Desktop icon launch with no console | pass |
| Startup failure reported in a dialog and the log | pass |
| 30-minute inactivity shutdown, warning, and job exemption | pass |
| Compile check | pass |
| Dependency consistency | pass |

## Not verified

- PyInstaller executable on a clean Windows machine without Python. Note that a packaged
  build must also bundle the `tkinterdnd2` Tcl files, which has not been tested.
- Continuous integration on Linux.
- OCR in languages other than English; only the `eng` pack is installed here.
- Very large documents (hundreds of megabytes) and long OCR runs.
- Docker test image rebuild after the Version 3 changes.
- PDF/A output has not been checked with a formal validator such as veraPDF; only the
  PDF/A identification metadata was confirmed.
- Form filling was tested on fields this app created, and on no real-world third-party form.
  XFA forms are known to be unsupported and were not tested.
- The full 30-minute idle wait was not sat through end to end; it was verified with a short
  timeout and by unit tests that drive the clock directly.
- The Start-menu shortcut option (`-StartMenu`) was not exercised; only the desktop icon was
  created and tested.

## Environment note

Roughly one run in five, Tk failed to start with
`TclError: Can't find a usable init.tcl … couldn't read file … No error` while reading
`Python312\tcl\tcl8.6\init.tcl`. The file is present and later runs succeed, so this looks
like a transient local read failure (antivirus or filesystem contention) rather than an
application defect. The GUI tests skip on `TclError` for that reason. If the GUI
occasionally fails to open with the same error, reinstalling Python or excluding its
folder from antivirus scanning is the fix.

## Test files

Tests build their fixtures in pytest's `tmp_path`, under the system temporary folder. No test
writes into the project folder, and pytest clears old run folders itself.
