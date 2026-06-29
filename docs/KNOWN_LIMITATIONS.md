# Known Limitations

- Office-to-PDF layout preservation depends on LibreOffice. It is usually good, but exact Microsoft Office layout matching is not guaranteed.
- LibreOffice is detected but not installed automatically.
- PDF text extraction works for text-based PDFs. Scanned PDFs need OCR, which is future work.
- Password-protected PDFs are detected and fail gracefully. Password entry support is future work.
- The dedicated Office-to-PDF GUI action is hidden when LibreOffice is missing; Auto conversion can still process non-Office files in a mixed batch and report Office failures.
- PDF to DOCX, compression, rotation, and OCR are not implemented in Version 1.
- Docker is intended for core tests only. Windows GUI support in Docker requires additional display configuration.
- The app was built and tested on Python 3.12.10. Python 3.13 should be reasonable, but Python 3.14 compatibility depends on third-party package wheel availability.
- TXT to PDF uses a built-in PDF font path that is best for simple text. Characters outside Latin-1 may be replaced in this first version.
