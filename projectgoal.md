# Project Goal

## Product Vision

Build a **local-first desktop PDF toolbox** inspired by the convenience and breadth of iLovePDF, while processing files entirely on the user's computer.

The application should let a non-technical Windows user complete common PDF tasks through a simple visual interface without uploading documents, creating an account, paying for an API, or requiring an internet connection after installation.

This is a functional recreation of common PDF workflows, **not** a copy of iLovePDF branding, source code, proprietary design assets, or online services.

## Core Value Proposition

> One private desktop application for converting, organizing, optimizing, editing, and securing PDFs locally.

The product should feel as straightforward as an online PDF utility:

1. Choose a tool.
2. Add one or more files.
3. Adjust a few clear options.
4. Run the task.
5. Open the generated files.

## Target Users

- People handling confidential personal, school, government, legal, finance, HR, or business documents.
- Users who prefer offline tools or have unreliable internet access.
- Windows users who want a simple alternative to command-line PDF utilities.
- Users who need repeatable batch processing without upload limits.

## Product Principles

1. **Local by default** — document contents never leave the computer.
2. **Safe by default** — never modify or delete original files.
3. **No silent overwrite** — generate a new numbered output name when a file already exists.
4. **Simple before powerful** — beginner-friendly defaults with advanced options available when needed.
5. **Clear failure messages** — explain what failed and how the user can resolve it.
6. **Modular tools** — each PDF operation should be testable independently of the GUI.
7. **Batch friendly** — support multiple files wherever the operation permits it.
8. **Transparent dependencies** — clearly identify features that need LibreOffice, Ghostscript, qpdf, Tesseract, or another local dependency.

## Functional Scope

### A. Convert to PDF

- JPG, JPEG, and PNG to PDF
- Multiple images to one PDF
- TXT to PDF
- Word to PDF
- PowerPoint to PDF
- Excel to PDF
- HTML to PDF

### B. Convert from PDF

- PDF pages to JPG or PNG
- PDF text extraction
- PDF to Word
- PDF to PowerPoint
- PDF to Excel
- PDF to PDF/A
- PDF to Markdown

### C. Organize PDF

- Merge PDFs
- Split PDFs
- Extract selected pages
- Remove selected pages
- Reorder pages with thumbnail previews
- Rotate selected pages
- Add pages from another PDF

### D. Optimize PDF

- Compress PDF with clear quality levels
- Repair recoverable PDF files
- OCR scanned PDFs into searchable PDFs

### E. Edit PDF

- Add text, images, shapes, and annotations
- Add watermarks
- Add page numbers
- Crop pages
- Fill and create basic form fields

### F. PDF Security

- Protect a PDF with a password
- Unlock a PDF when the user supplies the correct password
- Permanently redact selected content
- Compare two PDF versions
- Add a personal signature image or drawing

### G. Local Workflows

- Chain several tools into one reusable sequence.
- Save workflow settings locally.
- Process batches through the same workflow.

## Delivery Priorities

### Version 1 — Reliable Foundation

Deliver stable conversion, merge, split, extraction, safe output handling, logging, and a simple desktop GUI.

### Version 2 — Essential Local PDF Toolbox

Add the highest-value everyday tools: reorder, remove, extract, rotate, compress, watermark, page numbers, crop, protect, and unlock.

### Version 3 — Advanced Local Document Tools

Add OCR, repair, redaction, annotations, forms, PDF/A, richer conversions, comparison, and reusable workflows.

## Non-Goals for the Initial Releases

- Hosting a public cloud conversion service.
- User accounts, subscriptions, advertising, or telemetry.
- Multi-user real-time collaboration.
- Legally certified remote electronic-signature workflows.
- Exact pixel-for-pixel conversion parity with Microsoft Office.
- Copying another product's name, logo, visual identity, or proprietary implementation.

## Success Criteria

The project is successful when:

- All supported operations work without uploading document contents.
- A beginner can complete a common PDF task without reading technical documentation.
- Original files remain unchanged after every operation.
- Errors identify the affected file and provide an actionable message.
- Automated tests cover core processing, validation, output safety, and failure paths.
- A Windows installer or portable executable can run on a clean user machine.
- Optional local dependencies are detected and explained clearly.
- The architecture can accept a new PDF tool without rewriting the entire application.

## Definition of Done for Each Tool

A tool is complete only when it has:

- A processing function independent of the GUI.
- Input validation and clear option validation.
- Safe output naming and no-overwrite behavior.
- Batch behavior where appropriate.
- Friendly error handling and useful logging.
- Automated success and failure tests.
- GUI access with understandable labels and defaults.
- User documentation and known limitations.
