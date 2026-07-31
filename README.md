# Local PDF Toolbox

Local PDF Toolbox is a beginner-friendly Windows desktop app for converting, organizing,
optimizing, editing and securing PDFs on your own computer. There are no cloud APIs, no
uploads, no accounts, no telemetry and no paid services.

## Tools

40 tools in six categories. Everything runs offline. No account, no sign-up, no internet.

### Convert to PDF

| Tool | Notes |
| --- | --- |
| Auto convert to PDF | Mixed selection of images, TXT, HTML and Office files; one PDF per file |
| Images to PDF | JPG/PNG, one combined PDF or one per image, page size, orientation, fit, margin |
| TXT to PDF | Font size, page size, orientation, margin, Unicode font when one is available |
| HTML to PDF | Simple local HTML only; no JavaScript and no remote assets |
| Office to PDF | DOC/DOCX/PPT/PPTX/XLS/XLSX — needs LibreOffice |

### Convert from PDF

| Tool | Notes |
| --- | --- |
| PDF to JPG or PNG | Renders pages: DPI, JPG quality, grayscale, page selection |
| Extract images from PDF | Saves the embedded pictures in their original format |
| PDF to text | Page selection |
| PDF to Markdown | Headings guessed from font size; best effort |
| PDF to Word | Editable .docx — needs LibreOffice; best effort on complex layouts |
| PDF to Excel | Detected tables, or plain text lines, as worksheets |
| PDF to PowerPoint | One slide per page, page text in the speaker notes |
| PDF to PDF/A | PDF/A-1b, 2b or 3b for archiving — needs LibreOffice |

### Organize

| Tool | Notes |
| --- | --- |
| Merge PDFs | In the order you selected the files |
| Split PDF | Every page, chosen ranges, or fixed chunks of N pages |
| Rotate pages | 90 / 180 / 270, chosen pages |
| Extract pages | One PDF, or one PDF per page |
| Remove pages | Refuses to leave an empty PDF |
| Reorder pages | Type a new order |
| Insert pages from another PDF | At a chosen position |
| Organize pages visually | Thumbnail workspace: select, rotate, move, delete, then export |
| Compare two PDFs | Text difference report plus a side-by-side visual PDF |

### Optimize

| Tool | Notes |
| --- | --- |
| Compress PDF | Low / Balanced / Maximum; never larger than the original |
| Repair PDF | Rebuilds a damaged file structure |
| OCR PDF | Makes scans searchable — needs Tesseract; keeps the page image intact |

### Edit

| Tool | Notes |
| --- | --- |
| Add watermark | Text or image, opacity, angle, colour, once or tiled, page range |
| Add page numbers | Position, format, start number, margin |
| Crop pages | Margins in millimetres |
| Highlight or strike out text | Highlight, underline, strikeout or squiggly on found text |
| Add text | Any position in millimetres, size and colour |
| Add shape | Rectangle, ellipse, line or arrow, optionally filled |
| Add image | Position and width in millimetres, keeps proportions |
| List form fields | Writes the fillable fields to an editable JSON file |
| Fill PDF form | Type into an existing form, optionally flatten to lock the values |
| Create form field | Add a text box, checkbox or dropdown to be filled later |

### Security

| Tool | Notes |
| --- | --- |
| Protect with password | AES-256, with printing and copying permissions |
| Unlock PDF | Needs the correct password |
| Remove metadata | Document information and XMP |
| Redact PDF | Permanently deletes text, areas or images from the file |
| Sign PDF | Place a scanned or hand-drawn signature; visible, not certified |

Every PDF tool accepts the password of a protected input file, so you can work on
protected PDFs without unlocking them first.

## Windows setup

From this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then create the desktop icon, once:

```powershell
.\scripts\install_shortcut.ps1              # Desktop
.\scripts\install_shortcut.ps1 -StartMenu   # Desktop and Start menu
.\scripts\install_shortcut.ps1 -Remove      # remove the icons again
```

**Double-click "Local PDF Toolbox" on the desktop to start the app.** The shortcut runs
`pythonw.exe` from the project's virtual environment, so no console window appears. If the
app cannot start, it shows a dialog explaining why and writes the details to `logs\app.log`.

You can still start it from a terminal:

```powershell
.\.venv\Scripts\python.exe run_app.py
```

## Automatic shutdown

The app closes itself after **30 minutes** with no mouse or keyboard activity, so it never
sits open in the background. One minute before closing, a small window appears with a
countdown and a **Keep working** button; any click, key press or mouse movement cancels it.

A running operation always counts as activity, so a long OCR or compression job is never
interrupted.

To change the timeout, set `PDF_TOOLBOX_IDLE_MINUTES` before starting the app. `0` disables
automatic closing:

```powershell
$env:PDF_TOOLBOX_IDLE_MINUTES = "60"; .\.venv\Scripts\python.exe run_app.py
```

To make a different timeout permanent for the icon, set the variable for your user account
(`setx PDF_TOOLBOX_IDLE_MINUTES 60`), then sign out and back in.

## Using the app

1. Pick a tool from the category list on the left.
2. Drag files onto the file area, or press **Add files**, then choose an output folder.
3. Adjust the options shown for that tool. The defaults are safe.
4. Press **Run tool**, then **Open output folder** when it finishes.

Page selections accept single pages and ranges, for example `1-3,5`. Leaving the Pages
box blank means every page.

Positions for Add text, Add shape, Add image and Redact areas are millimetres measured
from the top-left corner of the page.

### Organize pages visually

Choose **Organize pages visually**, add one PDF, then press **Open workspace**. Click page
thumbnails to select them and use Rotate, Move and Delete. **Use this plan** writes the
result back into the tool as a page plan such as `3,1:90,2`, which you can also type by
hand or pass to the CLI.

### Signing

Choose **Sign PDF** and either browse to a signature image or press **Draw** to sign with
the mouse. Drawn signatures are saved as transparent PNGs under `output/signatures/` so
you can reuse them. A blank Pages box signs only the last page.

### Filling forms

Choose **Fill PDF form**, add the PDF, then press **Open workspace** to see every field and
type into it. **Use these values** writes them back into the tool. Turn on **Flatten** to
lock the values so the fields can no longer be edited.

If the PDF has no fields yet, use **Create form field** to add a text box, checkbox or
dropdown, then fill it. **List form fields** writes the field names to a JSON file, which is
handy for filling the same form repeatedly from the command line.

## Command line

The CLI uses the same tools as the GUI.

```powershell
.\.venv\Scripts\python.exe cli.py --list                     # every tool
.\.venv\Scripts\python.exe cli.py --help-tool watermark_pdf  # options for one tool
.\.venv\Scripts\python.exe cli.py rotate_pdf report.pdf -o output --set angle=180 --set pages=1-2
.\.venv\Scripts\python.exe cli.py compress_pdf big.pdf -o output --set level="Maximum compression"
.\.venv\Scripts\python.exe cli.py ocr_pdf scan.pdf -o output --set language=eng --set dpi=300
.\.venv\Scripts\python.exe cli.py redact_pdf deal.pdf -o output --set search_text="account number"
.\.venv\Scripts\python.exe cli.py organize_pdf report.pdf -o output --set plan=3,1:90,2
.\.venv\Scripts\python.exe cli.py compare_pdfs old.pdf new.pdf -o output
.\.venv\Scripts\python.exe cli.py fill_form form.pdf -o output --set "field_values=full_name=Mirza; agree=yes" --set flatten=true
.\.venv\Scripts\python.exe cli.py split_pdf book.pdf -o output --set every_n_pages=10
```

To convert a mixed batch of files to PDF in one go, use the auto tool:

```powershell
.\.venv\Scripts\python.exe cli.py auto_to_pdf notes.txt photo.png report.docx -o output
```

## Optional local engines

The header of the app shows whether each engine was detected. Tools that need a missing
engine are greyed out in the tool list; everything else keeps working.

### LibreOffice — Office to PDF, PDF to Word, PDF to PDF/A

Runs in headless mode. The app looks for:

- `soffice` or `soffice.exe` on PATH
- `C:\Program Files\LibreOffice\program\soffice.exe`
- `C:\Program Files (x86)\LibreOffice\program\soffice.exe`

### Tesseract — OCR PDF

The app looks for:

- `tesseract` or `tesseract.exe` on PATH
- `C:\Program Files\Tesseract-OCR\tesseract.exe`
- `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`

Language packs are read from the `tessdata` folder next to the executable, or from
`TESSDATA_PREFIX`. The detected language codes are listed in the app header; use them in
the Language box, joining several with `+`, for example `eng+deu`.

Neither engine is installed automatically. Install what you need from its official
website, then restart the app.

## Safety rules

- Input files are never modified or deleted.
- Existing output files are never overwritten. If `report.pdf` exists, the app writes
  `report_001.pdf`, then `report_002.pdf`, and so on.
- Generated names are sanitized for Windows-unsafe characters and reserved device names.
- Outputs cannot escape the output folder you chose.
- `logs/app.log` records tools, filenames and errors — never document contents.

## Running tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests build their own fixtures in pytest's temporary folder, so a test run never leaves
files inside the project. The GUI tests skip themselves when Tk cannot start.

## Project structure

```text
run_app.py            launches the GUI (what the desktop icon runs)
cli.py                registry-driven command line
requirements.txt      pinned dependencies
scripts/
  install_shortcut.ps1  creates or removes the desktop icon
  build_exe.ps1         optional PyInstaller build
assets/
  app_icon.ico          icon used by the shortcut, window and taskbar
  app_icon.png          icon for non-Windows window managers
  make_icon.py          regenerates both icons
src/
  app.py              tool dashboard
  gui_organize.py     thumbnail workspace for page organizing
  gui_forms.py        form-filling workspace
  gui_signature.py    signature drawing pad
  tool_registry.py    every tool, its inputs and its options
  converter.py        run_tool() orchestration and batch isolation
  file_validation.py  input, output and dependency validation
  output_paths.py     safe, non-overwriting output names
  pdf_tools.py        merge, split, image/text/markdown export
  pdf_pages.py        rotate, extract, remove, reorder, insert, page plans
  pdf_optimize.py     compress, repair
  pdf_edit.py         watermark, page numbers, crop
  pdf_annotate.py     highlight, add text, shapes, images
  pdf_forms.py        read, fill, flatten and create form fields
  pdf_redact.py       permanent content removal
  pdf_sign.py         signature placement
  pdf_compare.py      text and visual comparison
  pdf_export.py       PDF to Excel and PowerPoint
  pdf_security.py     protect, unlock, remove metadata
  ocr_tools.py        Tesseract OCR
  thumbnails.py       page thumbnail rendering
  image_tools.py      images to PDF
  text_tools.py       TXT to PDF
  html_tools.py       HTML to PDF
  office_tools.py     LibreOffice conversion
tests/                the test suite
docs/                 changelog, QA report, limitations, security review
output/               default place for generated files (and output/signatures/)
logs/                 app.log
```

Project notes live at the root: [projectgoal.md](projectgoal.md) for scope,
[plan.md](plan.md) for the roadmap, [progress.md](progress.md) for current state.

Adding a tool means writing one processing function and one `Tool(...)` entry in
`src/tool_registry.py`. The GUI and CLI pick it up with no interface changes. See
[CLAUDE.md](CLAUDE.md).

## Docker notes

The included Dockerfile runs the core tests, not the Windows GUI.

```powershell
docker build -t local-pdf-toolbox .
```

## Windows EXE packaging

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\scripts\build_exe.ps1
```

Packaging is not required for normal use.

## Troubleshooting

- **GUI does not open** — confirm Python 3.12+ and that dependencies are installed in `.venv`.
- **Office files do not convert** — install LibreOffice and make sure `soffice.exe` is on
  PATH or in a standard install folder, then restart the app.
- **"password protected"** — type the PDF's password into the tool's password box.
- **Page range error** — use numbers such as `1-3,5`, and make sure the pages exist.
- **PDF to text returns little text** — the PDF is probably scanned. Run **OCR PDF** first.
- **OCR PDF is greyed out** — Tesseract was not detected; install it and restart the app.
- **"Language pack is not installed"** — install that Tesseract language file, or use one
  of the codes listed in the app header.
- **Highlight or Redact says nothing matched** — the PDF has no text layer (run OCR first),
  or the spelling or page selection does not match.
- **Drag and drop does nothing** — the header will say if it is unavailable; use Add files.
- **Double-clicking the icon does nothing** — check `logs\app.log`. If the virtual
  environment moved, run `.\scripts\install_shortcut.ps1` again to point the icon at the new path.
- **The app closed by itself** — that is the 30-minute inactivity timeout. Reopen it from
  the icon, or raise `PDF_TOOLBOX_IDLE_MINUTES`.
- **Compression says "already well compressed"** — the file was already small; the app
  copies it unchanged rather than making it bigger.
- **A PDF will not open in any tool** — try Repair PDF first.
- Detailed errors are written to `logs/app.log`.

## What this app does not do

Stated plainly so nothing is a surprise:

- No cloud storage import, share links, or task history — everything is local by design.
- **HTML to PDF takes a local file, not a web address.** Fetching a URL would mean a network
  request, which this app deliberately never makes. Save the page yourself first.
- **Sign PDF** places a visible signature. It is not a cryptographic digital signature and
  carries no legal certification.
- **PDF to Word**, **PDF to Excel**, **PDF to PowerPoint** and **PDF to Markdown** are
  best-effort reconstructions. Complex layouts will need tidying up.
- Forms support standard AcroForm fields. XFA forms, the kind some government PDFs use, are
  not supported.
- Scanning from a camera or scanner device is not included; scan with your own software
  first, then run **OCR PDF**.
- Editing positions are typed in millimetres; there is no click-on-the-page placement or
  live preview yet.
- See [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for the full list.

## Privacy

All processing runs locally. The app does not upload files, call cloud APIs, send
telemetry or use paid services. Passwords are held only in memory for the operation and
are never written to `logs/app.log`.
