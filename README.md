# Local PDF Converter

Local PDF Converter is a Windows desktop PDF toolkit with an iLovePDF-style card interface. It does not use accounts, cloud APIs, telemetry, uploads, or paid services.

## What Works Locally

Works without LibreOffice:

- PNG/JPG/JPEG to PDF
- Multiple images to one PDF
- TXT to PDF
- Merge multiple PDFs
- Split PDFs into individual pages or selected ranges
- PDF pages to PNG images
- PDF text extraction
- Organize, rotate, crop, repair, compress, watermark, page-number, edit, form-fill, sign-image, compare, protect, unlock, and true-redact PDFs
- PDF to JPG, Markdown, Word, PowerPoint, and Excel
- Local HTML files to PDF
- Scan/document images to a single PDF

Requires LibreOffice:

- DOC/DOCX to PDF
- PPT/PPTX to PDF
- XLS/XLSX to PDF
- PDF to PDF/A-1

Requires the Tesseract desktop binary:

- OCR PDF (`pytesseract` is installed from `requirements.txt`, but does not install Tesseract itself)

Optional local intelligence:

- AI Summarizer and Translate are off by default
- They run only after the explicit panel toggle is enabled and only call localhost Ollama at `127.0.0.1:11434`

If LibreOffice is missing, the app still opens and non-Office features continue to work.
Cards that require a missing external binary remain visible and explain why they are unavailable.

## Windows Setup

From this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

Run the desktop app:

```powershell
.\.venv\Scripts\python.exe run_app.py
```

After setup, double-click `launch_app.vbs` in this folder to launch the app without a console window. You can create a personal Windows shortcut to that launcher if desired. The app closes automatically after 30 minutes without keyboard or mouse activity. An active conversion is never interrupted by the idle timer.

The 30-minute default needs no configuration. For testing or a custom local timeout, set `LOCAL_PDF_CONVERTER_IDLE_TIMEOUT_SECONDS` before starting the app. Invalid values safely fall back to 1,800 seconds.

You can also use the small CLI compatibility wrapper for automatic file-to-PDF conversion:

```powershell
.\.venv\Scripts\python.exe convert_to_pdf.py "C:\path\to\your\notes.txt" -o output
```

## LibreOffice Support

Office conversion is performed with LibreOffice in headless mode. The app checks:

- `soffice` or `soffice.exe` on PATH
- `C:\Program Files\LibreOffice\program\soffice.exe`
- `C:\Program Files (x86)\LibreOffice\program\soffice.exe`

LibreOffice is not installed automatically. Install it yourself from the official LibreOffice website if you need Office-to-PDF conversion, then restart the app.

## Running Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests generate simple sample files under `sample_files/generated_pytest/` and conversion logs under `logs/`.

## Project Structure

```text
launch_app.vbs            Portable console-free Windows launcher
run_app.py                Desktop application entry point
convert_to_pdf.py         Command-line compatibility entry point
requirements*.txt         Runtime and development dependencies
Dockerfile                Containerized core test environment

src/                      Application code and conversion services
tests/                    Automated test suite
scripts/                  Developer and packaging utilities
docs/                     Documentation, indexed by purpose
sample_files/              Local fixtures and generated test samples
output/                    Default converted-file destination
logs/                      Local application logs
```

The GUI calls `src.converter`, and the conversion logic lives in separate service modules so the core can later be reused by a CLI, local web UI, Docker test flow, or packaged Windows app.

Start with [`docs/README.md`](docs/README.md) for documentation or [`scripts/README.md`](scripts/README.md) for developer utilities.

## No-Overwrite Behavior

Original input files are never deleted or modified. Existing output files are not overwritten. If `report.pdf` already exists, the app creates `report_001.pdf`, `report_002.pdf`, and so on.
Generated output names are sanitized for Windows-unsafe characters and reserved device names.

## Tool Notes

For the Split PDF action, leave the Pages field blank to split every page into a separate PDF. Enter ranges such as `1-3,5` to create selected page outputs.

PDF-to-Word/PowerPoint/Excel extraction is text/table-first and complex layout is approximate. Sign places an image signature and is not a cryptographic digital signature. Unlock requires the correct user password; it does not crack or brute-force passwords. Redact permanently removes matching content before saving.

## Docker Notes

The included Dockerfile is for core conversion tests, not the Windows desktop GUI. Running GUI apps from Docker on Windows needs extra display setup and is outside this first version.

Build and test:

```powershell
docker build -t local-pdf-converter .
docker run --rm local-pdf-converter
```

## Future Windows EXE Packaging

PyInstaller can be tried later after the app is stable:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\scripts\build_exe.ps1
```

Packaging is not required for normal use. Run `python run_app.py` during development.

## Troubleshooting

- If the GUI does not open, confirm Python 3.12+ is installed and dependencies are installed in `.venv`.
- If Office files do not convert, install LibreOffice and make sure `soffice.exe` is on PATH or in a standard install folder.
- If the Office-to-PDF action is missing, LibreOffice was not detected. Other actions are still available.
- If PDF split reports a page range error, use numbers like `1-3,5` and make sure the pages exist in the PDF.
- If PDF text extraction returns little or no text, install the Tesseract desktop binary and use OCR PDF.
- Detailed errors are written to `logs/app.log`. Logs record actions, filenames, output names, and technical failures, but not document contents.

## Privacy

All conversions run locally. The app does not upload files, call cloud APIs, send telemetry, or use paid services.
