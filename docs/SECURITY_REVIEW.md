# Security Review

## Local-Only Behavior

The application uses local Python libraries and optional local LibreOffice headless conversion. No cloud APIs, telemetry, analytics, or upload behavior were found or added.

## File Access Boundaries

The app reads user-selected input files and writes to the selected output folder. Original input files are not deleted or modified.

Hardening added in this pass:

- Output filenames are sanitized for Windows-unsafe characters.
- Windows reserved device names such as `CON` are avoided.
- Generated output paths are checked to ensure they remain inside the selected output folder.
- Existing output files are not overwritten; numbered names are generated.

## Subprocess Safety

LibreOffice conversion uses `subprocess.run()` with a list of arguments, `shell=False` by default, captured stdout/stderr, and a timeout. No shell command construction is used for user-selected document paths.

LibreOffice is detected from PATH or common Windows install locations. It is not installed automatically.

## Logging Privacy

The app logs technical activity to `logs/app.log` and does not log document contents.

Hardening added in this pass:

- New persistent conversion logs avoid full output paths and record filenames/output names instead.
- Expected validation failures log as warnings rather than full stack traces.
- Unexpected exceptions still include stack traces for debugging.

Note: historical log entries from before this pass may contain full paths.

## Dependency Notes

Top-level dependencies, all version-constrained in `requirements.txt`:

- customtkinter
- pymupdf
- pypdf
- pikepdf
- cryptography (lets pypdf read AES-256 protected PDFs)
- pillow
- reportlab
- openpyxl (PDF to Excel)
- python-pptx (PDF to PowerPoint)
- tkinterdnd2 (optional drag-and-drop)
- pytest

`img2pdf` was removed in Version 2 because image conversion now goes through PyMuPDF.

Optional external programs, detected and never installed automatically: LibreOffice
(Office conversion, PDF to Word, PDF/A) and Tesseract (OCR).

`pip check` reported no broken requirements.

## Version 2 Additions (2026-07-31)

### Passwords

- Passwords are read from GUI entry fields masked with `*`, passed as function arguments,
  and never written to `logs/app.log` or to disk.
- Protect uses AES-256 (pikepdf revision 6 encryption). Permission flags for printing and
  text extraction are set, but PDF permissions are advisory and cannot be enforced against
  a reader that has the password.
- Unlock requires the correct password; a wrong password writes no output file.
- Wrong-password and missing-password cases raise plain `ValueError` messages, so the GUI
  shows a sentence rather than a stack trace.

### Metadata and residual data

- Remove metadata clears document information and XMP metadata. It does not remove text
  hidden in page content, embedded attachments or JavaScript. This is documented in
  `docs/KNOWN_LIMITATIONS.md`.
- Crop hides content by shrinking the crop box; cropped content is still present in the
  file. True redaction is not implemented and the GUI hint says so.

### Temporary files

- Compression and Office conversion use `tempfile.TemporaryDirectory` inside the chosen
  output folder, so temporary data never lands in a shared system temp directory and is
  removed on success and on failure. A test asserts no `.compress_*` folder remains.

## Security Concerns Found and Fixed

- Path-like or unsafe output basenames were not sanitized strongly enough. Fixed.
- PDF-to-PNG created an output folder before validating encrypted PDFs. Fixed.
- Persistent logs included full output paths. Reduced for new log entries.

## Version 3 Additions (2026-07-31)

### Redaction

- Redaction uses PyMuPDF `add_redact_annot` followed by `apply_redactions(images=2)`, so
  matched content is deleted from the page's content stream and partially covered images
  are rasterised. A test asserts the redacted string is absent from the output's extracted
  text, and another asserts the page has no images left after image redaction.
- Redaction is not a guarantee of complete removal. Text drawn as an image, text split
  across lines, metadata and embedded attachments are not caught by a text search. The GUI
  hint and `docs/KNOWN_LIMITATIONS.md` both say so, and the tool writes no output at all
  when nothing matched, rather than implying success.

### OCR

- OCR runs entirely locally through Tesseract; no image or text leaves the machine.
- The recognised text is stored as an invisible layer over the unchanged page image, so the
  original scan is never replaced by a machine guess.
- The language code is validated against the installed language files before Tesseract is
  invoked, so no unchecked value reaches the OCR call.

### Signing

- Sign PDF places a visible image. It is deliberately **not** presented as a digital
  signature: the success note and the docs state that it is not certified. No private key,
  certificate or trust store is involved.
- Signatures drawn in the app are written to `output/signatures/` as ordinary PNGs. Users
  should treat that folder as sensitive, since a signature image can be reused by anyone
  who obtains it.

### Subprocess safety

- The new LibreOffice conversions still use `subprocess.run()` with an argument list,
  `shell=False`, captured output and a timeout. Import filters and filter options are
  literals defined in `src/office_tools.py`, never built from user input; only the input
  and output paths vary.

### Drag and drop

- Dropped paths are filtered against `SUPPORTED_INPUT_EXTENSIONS` and `Path.is_file()`
  before being added, and the count of ignored files is reported to the user.

## Remaining Recommendations

- Keep dependencies updated through the local virtual environment.
- Avoid opening untrusted PDFs from unknown sources when not necessary; PDF parsers are complex.
- Consider a "clear logs" button later if users want to remove local troubleshooting history.
- Consider offering to delete a drawn signature PNG after it has been applied, or storing it
  outside the `output/` folder that users are likely to share.
- Verify PDF/A output with a formal validator such as veraPDF before relying on it for
  archival compliance.
- Password entry is now available on every PDF tool; the earlier recommendation is done.

