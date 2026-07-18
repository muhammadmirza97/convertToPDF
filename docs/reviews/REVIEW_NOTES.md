# Review Notes

## Review Timestamp

2026-06-30 06:34:50 +08:00

## Environment

- Project: Local PDF Converter
- Operating system detected: Microsoft Windows 11 Home
- Python detected: Python 3.12.10
- Virtual environment used: yes, `.venv`
- LibreOffice detected: no, detection returned `NOT_FOUND`
- Dependencies changed during this pass: no new packages added

## What Was Reviewed

The app was reviewed as a local-only Windows desktop converter. The pass focused on correctness, GUI validation, batch behavior, output file safety, logging privacy, LibreOffice behavior, test coverage, and documentation accuracy.

## Bugs Found and Fixed

- Output filename generation accepted Windows-unsafe characters and reserved device names too directly. Added `sanitize_base_name()` and path containment checks.
- Invalid split-page text such as `one-three` produced a raw integer parsing error. It now raises a beginner-friendly page range message.
- PDF-to-PNG created an output folder before validating whether a PDF was encrypted. It now opens and validates the PDF before creating page image folders.
- Persistent logs stored full output paths. Logs now record action, counts, output names, and filenames without full output paths.
- Predictable user input failures were logged with noisy stack traces. Expected `ValueError` failures now log as warnings; unexpected exceptions still include stack traces.
- App startup and conversion action logging were incomplete. Startup and selected action are now logged.
- The dedicated Office-to-PDF GUI action remained visible when LibreOffice was missing. It is now hidden when LibreOffice is not detected.

## Features Verified Working

- GUI construction and short event loop smoke test
- App name: Local PDF Converter
- Multiple file validation
- Output folder validation
- Disabled Convert button logic through validation tests and GUI smoke
- PNG/JPG/JPEG to PDF
- Multiple images to one PDF
- TXT to PDF
- PDF to PNG images
- PDF to TXT text extraction
- PDF merge
- PDF split with blank page ranges and selected ranges
- Batch conversion with partial failure reporting
- Missing LibreOffice validation
- Unsupported file type rejection
- Invalid output folder rejection
- Password-protected PDF graceful failure path
- No-overwrite output naming
- Windows-safe output filename sanitizing

## Partially Working

- Office-to-PDF is implemented through LibreOffice headless conversion, but could not be verified on this laptop because LibreOffice was not detected.
- Auto conversion can process mixed batches; if a PDF is included, it reports a per-file failure asking the user to choose a PDF action.

## Not Working or Not Implemented

- PDF to DOCX
- PDF compression
- PDF rotation
- Password entry for encrypted PDFs
- OCR for scanned PDFs
- Docker GUI operation on Windows

## Commands Run

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src run_app.py convert_to_pdf.py tests
.\.venv\Scripts\python.exe --version
Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption
.\.venv\Scripts\python.exe -c "from src.app import LocalPDFConverterApp; app = LocalPDFConverterApp(); app.after(200, app.destroy); app.mainloop(); print('GUI_SMOKE_OK')"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "from src.office_tools import find_libreoffice; print(find_libreoffice() or 'NOT_FOUND')"
Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz'
Get-Content -Tail 40 -LiteralPath 'logs\app.log'
```

## Test Results

Initial baseline:

```text
12 passed in 0.97s
```

After hardening and regression tests:

```text
22 passed in 0.91s
```

Compile check:

```text
passed with no output
```

GUI smoke:

```text
GUI_SMOKE_OK
```

Dependency check:

```text
No broken requirements found.
```

## Tests Added

- Windows-unsafe output filename sanitizing
- Reserved Windows filename handling
- Derived output folder containment
- Blank/unsafe basename fallback
- Unsupported file type rejection
- Invalid output folder path rejection
- Invalid split page range message
- Encrypted PDF graceful failure
- Missing LibreOffice validation
- Auto batch partial failure reporting

## Remaining Known Issues

- Real Office-to-PDF behavior still needs verification on a machine with LibreOffice installed.
- Scanned PDFs need OCR, which is not included.
- TXT to PDF may replace some non-Latin characters because it uses a simple built-in PDF font path.
- Existing historical lines in `logs/app.log` from before this pass may still include full paths. New persistent log lines are less path-heavy.

## Recommended Next Steps

- Install LibreOffice manually if Office-to-PDF is needed, then run a DOCX/PPTX/XLSX conversion smoke test.
- Consider Version 2 features in this order: PDF rotation, password entry, compression, then OCR.
- Add a dedicated CLI command module if command-line use becomes important.
- Have a human try the GUI with real files and judge whether wording and layout feel beginner-friendly.
