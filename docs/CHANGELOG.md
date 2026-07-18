# Changelog

## 2026-07-19 Project Navigation Cleanup

- Kept user-facing launchers and required entry points at the project root.
- Grouped design, reference, review, and support documents into named documentation folders.
- Moved packaging utilities into `scripts/` and made the build script independent of the current working directory.
- Added documentation and scripts indexes for easier navigation.

## 2026-07-19 Categorized All-Tools Menu

- Replaced the compact all-tools selector with a wide seven-section mega-menu matching the supplied reference.
- Grouped every available tool exactly once across organize, optimize, convert-to, convert-from, edit, security, and intelligence sections.
- Kept unavailable local-dependency tools visible with muted indicators and their existing explanatory message.

## 2026-07-19 iLovePDF-Style Tool Pages

- Refined the Local PDF brand header, active navigation, hero typography, filter pills, and five-column tool grid to match the supplied visual references.
- Added a spacious file-selection stage with a large red local-file button, followed by a separate options-and-progress workspace after selection.
- Made native file pickers tool-specific while retaining offline-only behavior and excluding account and cloud controls.
- Extended Windows detection for common Tesseract installation locations and isolated LibreOffice headless conversions from the user's LibreOffice profile.

## 2026-07-18 Offline PDF Toolkit

- Rebuilt the desktop home screen with Local PDF navigation, hero copy, category filter pills, and 31 tool cards.
- Added offline organize, optimize, convert, edit, security, and intelligence service routes while preserving the worker-thread/event-queue UI lifecycle.
- Added AES-256 protection, password-only unlock, permanent redaction, form fill/create helpers, Markdown extraction, local HTML conversion, and document/image export tools.
- Added optional Tesseract OCR, LibreOffice PDF/A, and explicitly enabled localhost-only Ollama intelligence features with graceful unavailable states.
- Added generated-PDF regression coverage for rotation, compression, encryption, watermarking, page numbers, crop boxes, redaction, page order, forms, Markdown, and extended smoke paths.

## 2026-07-18 Windows Launcher and Idle Shutdown

- Added a double-click Windows launcher that starts the app without leaving a console window open.
- Added automatic shutdown after 30 minutes without keyboard or mouse activity.
- Added the optional `LOCAL_PDF_CONVERTER_IDLE_TIMEOUT_SECONDS` override while retaining a no-setup 1,800-second default.
- Protected active conversions from being interrupted by the idle timer.
- Added regression tests for timer reset, automatic closing, and conversion protection.

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

- Rewrote `docs/reviews/REVIEW_NOTES.md` for this review pass.
- Added `docs/reviews/QA_REPORT.md`.
- Added `docs/reviews/SECURITY_REVIEW.md`.
- Added this changelog.
- Updated README and known limitations.

