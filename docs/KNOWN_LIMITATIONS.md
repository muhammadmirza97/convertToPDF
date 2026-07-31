# Known Limitations

## External dependencies

- **LibreOffice** is needed for Office to PDF, PDF to Word and PDF to PDF/A. It is detected,
  never installed automatically. Those tools are disabled when it is missing.
- **Tesseract** is needed for OCR PDF, along with at least one language pack. Only the
  language files installed on the machine can be used.
- Office-to-PDF layout depends on LibreOffice. It is usually good, but exact Microsoft
  Office layout matching is not guaranteed.

## Conversion fidelity

- **PDF to Word** re-imports the PDF through LibreOffice Writer. Simple text documents come
  out well; multi-column layouts, tables and precise spacing usually need tidying up.
- **PDF to Excel** detects ruled tables first, then whitespace-aligned columns. Tables with
  no ruling and irregular spacing may be missed, in which case the Text lines mode writes
  one row per line. Merged cells, formulas and formatting are not reproduced.
- **PDF to PowerPoint** puts a picture of each page on a slide. Slide text is therefore not
  directly editable; the extracted text is placed in the speaker notes instead.
- **PDF to PDF/A** uses the LibreOffice Draw export path, so the page is rebuilt. Text stays
  selectable but complex vector content can shift slightly, and the file usually grows
  because fonts are embedded.
- **PDF to Markdown** guesses heading levels from font sizes. Tables, multi-column layouts,
  images and footnotes are not reconstructed.
- **HTML to PDF** takes a local `.html` file, not a web address: fetching a URL would mean a
  network request, which this app deliberately never makes. It uses the local PyMuPDF story
  renderer, which handles headings, paragraphs, lists, tables, links, basic CSS and local
  images. JavaScript, flexbox, grid, remote stylesheets and remote images are ignored, so
  complex pages will not match a browser.
- **TXT to PDF** uses the widest-coverage TrueType font found on the machine (Arial or Segoe
  UI on Windows, DejaVu Sans on Linux, Bitstream Vera as a bundled fallback). Chinese,
  Japanese, Korean and Arabic need a font that covers those scripts.

## OCR

- OCR quality depends on the scan. Skewed, low-contrast or below-200-DPI scans give poor
  results; 300 DPI is a good default.
- The recognised text is an invisible layer, so a misread word is searchable only as the
  misread text. Always keep the original scan.
- Handwriting, tables and multi-column scans are not reconstructed as structure.
- OCR is slower than every other tool: expect a few seconds per page.

## Page operations and editing

- **Crop** changes the visible crop box. It hides content rather than deleting it, so
  cropped areas can still be recovered. Use Redact PDF to remove content.
- Crop margins are applied to the unrotated page box, so results on rotated pages may not
  match what you see on screen.
- Positions for Add text, Add shape, Add image and redaction areas are typed in
  millimetres. There is no click-on-the-page placement or live preview yet.
- Highlight, redaction by text, and text comparison all need a text layer. Run OCR PDF on
  scans first.
- The Organize workspace selects pages by clicking; it does not support dragging a
  thumbnail to a new position. Move left and Move right do the reordering.
- Bookmarks, form fields, annotations and tagged-PDF structure are not always preserved by
  page-level operations; document information metadata is preserved.

## Forms

- Only standard AcroForm fields are supported. XFA forms, used by some government and bank
  PDFs, are not readable by this app; open those in Adobe Acrobat Reader instead.
- Flattening is one way. Once the values are drawn as page content the fields are gone, so
  keep the unflattened copy if you may need to change an answer.
- Flattened text is drawn in Helvetica at the field's font size, left-aligned near the
  bottom of the box. Right-aligned, centred and multi-line fields will not match exactly how
  a PDF reader displayed them.
- Created fields are deliberately basic: no validation rules, no calculations, no JavaScript,
  no radio-button groups, and no tab-order control.
- Digital signature fields are listed but cannot be signed; Sign PDF places a visible image
  instead.

## Extracting images

- Extract images returns the pictures actually stored in the file. A page that is drawn as
  vector graphics or text contains no embedded image, so nothing is extracted; use PDF to
  JPG or PNG to render the page instead.
- Some PDFs store one photograph as many small tiles. Those come out as separate files.
- The extracted image is the stored original, which may be larger or smaller than it appears
  on the page and may include areas the page crops out.

## Redaction

- Redaction removes the matched content, but review the output before sharing. Text that
  spans two lines, is drawn as an image, or is stored in metadata or attachments will not
  be caught by a text search.
- Only the pages you select are processed. A blank page list covers every page.

## Optimization

- Compression is driven by PyMuPDF. Maximum compression re-encodes images at 96 DPI with
  JPEG quality 45, which visibly softens photos. Use Low compression for lossless work.
- If compression cannot make a file smaller, the app copies the original unchanged and says
  so, rather than writing a larger file.
- Repair rebuilds the file structure. Content that is already missing cannot be recovered.

## Security and signing

- Protect uses AES-256 (revision 6). Permission flags are advisory: PDF readers are
  expected to honour them, but they cannot be enforced once a reader has the password.
- Unlock requires the correct password. There is no password recovery, by design.
- **Sign PDF places a visible signature only.** It is not a cryptographic digital
  signature, it does not use a certificate, and it makes no legal certification claim.
- Remove metadata clears document information and XMP metadata. It does not remove text
  hidden inside page content, embedded file attachments, or JavaScript.

## Comparison

- Comparison is page-by-page and positional. Inserting a page early in the document makes
  every later page report as changed.
- The visual report marks a page as changed when any pixel differs, including a one-pixel
  rendering difference. Use it to find pages worth reviewing, not as proof of a change.

## Application

- Drag-and-drop needs the optional `tkinterdnd2` package; the header says when it is
  unavailable and the Add files button always works.
- A running operation cannot be cancelled yet.
- There is no scan-from-camera or scan-from-scanner capture, and no saved multi-step
  workflows.
- No metadata inspection screen; `read_metadata()` exists but only the removal tool is
  exposed in the interface.
- Docker is intended for core tests only. Running the Windows GUI in Docker needs extra
  display configuration.
- Built and tested on Python 3.12 on Windows 11. Python 3.13 should be reasonable; later
  versions depend on third-party wheel availability.
- The PyInstaller build script has not been verified on a clean machine.
