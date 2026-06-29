"""Shared configuration for Local PDF Converter."""

from __future__ import annotations

from pathlib import Path


APP_NAME = "Local PDF Converter"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {".txt"}
OFFICE_EXTENSIONS = {".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"}
SUPPORTED_INPUT_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS | TEXT_EXTENSIONS | OFFICE_EXTENSIONS

ACTION_AUTO = "Auto: Convert selected files to PDF"
ACTION_IMAGES_TO_SINGLE_PDF = "Images to single PDF"
ACTION_PDF_TO_PNG = "PDF to PNG images"
ACTION_PDF_TO_TEXT = "PDF to text"
ACTION_MERGE_PDFS = "Merge PDFs"
ACTION_SPLIT_PDF = "Split PDF"
ACTION_TXT_TO_PDF = "TXT to PDF"
ACTION_OFFICE_TO_PDF = "Office to PDF"

ACTIONS = [
    ACTION_AUTO,
    ACTION_IMAGES_TO_SINGLE_PDF,
    ACTION_PDF_TO_PNG,
    ACTION_PDF_TO_TEXT,
    ACTION_MERGE_PDFS,
    ACTION_SPLIT_PDF,
    ACTION_TXT_TO_PDF,
    ACTION_OFFICE_TO_PDF,
]

