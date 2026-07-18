# QA Report

## Test Plan

The QA pass covered baseline tests, regression tests for bugs found during review, GUI import/event-loop smoke testing, compile checks, dependency checks, and feature-level conversion paths that do not require LibreOffice.

## Automated Checks

Commands run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src run_app.py convert_to_pdf.py tests
.\.venv\Scripts\python.exe -m pip check
```

Results:

```text
22 passed in 0.91s
No broken requirements found.
compileall succeeded with no output
```

## Manual and Smoke Checks

Commands run:

```powershell
.\.venv\Scripts\python.exe -c "from src.app import LocalPDFConverterApp; app = LocalPDFConverterApp(); app.after(200, app.destroy); app.mainloop(); print('GUI_SMOKE_OK')"
.\.venv\Scripts\python.exe -c "from src.office_tools import find_libreoffice; print(find_libreoffice() or 'NOT_FOUND')"
Get-Content -Tail 40 -LiteralPath 'logs\app.log'
```

Results:

```text
GUI_SMOKE_OK
NOT_FOUND
```

Log review showed conversion success/failure entries and confirmed new logging behavior records less full-path detail.

## Pass Summary

- File validation: pass
- Output path generation: pass
- No-overwrite filename behavior: pass
- Windows-safe output name sanitizing: pass
- Image to PDF: pass
- Multiple images to one PDF: pass
- TXT to PDF: pass
- PDF merge: pass
- PDF split: pass
- PDF text extraction: pass
- PDF to PNG: pass
- Unsupported file type handling: pass
- Invalid output folder handling: pass
- Missing LibreOffice behavior: pass
- Encrypted PDF failure handling: pass
- GUI smoke: pass
- Compile check: pass
- Dependency consistency: pass

## Skipped or Not Fully Verified

- Real DOC/DOCX/PPT/PPTX/XLS/XLSX to PDF conversion was not run because LibreOffice was not detected.
- Full manual GUI conversion was not performed interactively in this automated pass; the GUI was constructed and its event loop was smoke-tested.

## Test Files

Generated test files are created only inside `sample_files/generated_pytest/`.
