# Changelog

## 2026-07-17 Portfolio Blueprint Execution

### Reliability and Security

- Pinned runtime and development dependencies and removed the unused `img2pdf` package.
- Fixed Docker builds from a clean clone and documented the container test command.
- Removed the obsolete repository setup script that could delete Git history.
- Made output-folder validation side-effect free and validated encrypted PDFs before reserving output paths.
- Snapshotted GUI state before worker-thread conversion and locked file/folder controls during a run.
- Added bounded log rotation and suppressed LibreOffice console windows on Windows.

### Tests and Documentation

- Added regression tests for side-effect-free folder validation and encrypted-PDF extraction.
- Updated setup, CLI, and Docker commands in the README.

## 2026-06-30 Review, Debugging, Hardening, and Improvement Pass

### Bug Fixes

- Sanitized generated output basenames for Windows-unsafe characters and reserved names.
- Added containment checks so generated outputs stay inside the selected output folder.
- Replaced raw split-page parsing errors with friendly validation messages.
- Prevented PDF-to-PNG from creating output folders before encrypted PDF validation.
- Reduced noisy stack traces for expected user input failures.

### UX Improvements

- Hid the dedicated Office-to-PDF action when LibreOffice is missing.
- Updated LibreOffice status text in the GUI.
- Logged startup and selected conversion action.
- Made README troubleshooting clearer for split page ranges and missing LibreOffice.

### Test Improvements

- Increased automated tests from 12 to 22.
- Added tests for unsafe output names, reserved names, unsupported files, invalid output folders, encrypted PDFs, missing LibreOffice, and partial batch failures.

### Documentation Improvements

- Rewrote `docs/REVIEW_NOTES.md` for this review pass.
- Added `docs/QA_REPORT.md`.
- Added `docs/SECURITY_REVIEW.md`.
- Added this changelog.
- Updated README and known limitations.

