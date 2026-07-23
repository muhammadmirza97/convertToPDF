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

Top-level dependencies remain:

- customtkinter
- pymupdf
- pypdf
- pillow
- img2pdf
- reportlab
- pytest

`pip check` reported no broken requirements.

## Security Concerns Found and Fixed

- Path-like or unsafe output basenames were not sanitized strongly enough. Fixed.
- PDF-to-PNG created an output folder before validating encrypted PDFs. Fixed.
- Persistent logs included full output paths. Reduced for new log entries.

## Remaining Recommendations

- Keep dependencies updated through the local virtual environment.
- Avoid opening untrusted PDFs from unknown sources when not necessary; PDF parsers are complex.
- Add password-entry support before attempting encrypted PDF conversions.
- Consider a "clear logs" button later if users want to remove local troubleshooting history.

