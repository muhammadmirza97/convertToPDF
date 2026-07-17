# Local PDF Converter

Local PDF Converter is a beginner-friendly Windows desktop app for converting documents, images, and PDFs on your own computer. It does not use cloud APIs, telemetry, uploads, or paid services.

## What Works Locally

Works without LibreOffice:

- PNG/JPG/JPEG to PDF
- Multiple images to one PDF
- TXT to PDF
- Merge multiple PDFs
- Split PDFs into individual pages or selected ranges
- PDF pages to PNG images
- PDF text extraction

Requires LibreOffice:

- DOC/DOCX to PDF
- PPT/PPTX to PDF
- XLS/XLSX to PDF

If LibreOffice is missing, the app still opens and non-Office features continue to work.
The dedicated Office-to-PDF menu option is hidden when LibreOffice is not detected.

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
run_app.py
convert_to_pdf.py
requirements.txt
src/
  app.py
  converter.py
  file_validation.py
  pdf_tools.py
  office_tools.py
  image_tools.py
  text_tools.py
  output_paths.py
  logger.py
  config.py
tests/
docs/
sample_files/
output/
logs/
```

The GUI calls `src.converter`, and the conversion logic lives in separate service modules so the core can later be reused by a CLI, local web UI, Docker test flow, or packaged Windows app.

## No-Overwrite Behavior

Original input files are never deleted or modified. Existing output files are not overwritten. If `report.pdf` already exists, the app creates `report_001.pdf`, `report_002.pdf`, and so on.
Generated output names are sanitized for Windows-unsafe characters and reserved device names.

## Splitting PDFs

For the Split PDF action, leave the Pages field blank to split every page into a separate PDF. Enter ranges such as `1-3,5` to create selected page outputs.

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
.\build_exe.ps1
```

Packaging is not required for normal use. Run `python run_app.py` during development.

## Troubleshooting

- If the GUI does not open, confirm Python 3.12+ is installed and dependencies are installed in `.venv`.
- If Office files do not convert, install LibreOffice and make sure `soffice.exe` is on PATH or in a standard install folder.
- If the Office-to-PDF action is missing, LibreOffice was not detected. Other actions are still available.
- If PDF split reports a page range error, use numbers like `1-3,5` and make sure the pages exist in the PDF.
- If PDF text extraction returns little or no text, the PDF may be scanned. OCR is not included in this version.
- Detailed errors are written to `logs/app.log`. Logs record actions, filenames, output names, and technical failures, but not document contents.

## Privacy

All conversions run locally. The app does not upload files, call cloud APIs, send telemetry, or use paid services.
