"""Shared configuration for Local PDF Toolbox."""

from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "Local PDF Toolbox"
APP_VERSION = "2.0.0"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
ASSETS_DIR = PROJECT_ROOT / "assets"
APP_ICON_ICO = ASSETS_DIR / "app_icon.ico"
APP_ICON_PNG = ASSETS_DIR / "app_icon.png"

# The app closes itself after this long with no mouse or keyboard activity. A running
# operation always counts as activity, so a long OCR job is never interrupted.
DEFAULT_INACTIVITY_TIMEOUT_MINUTES = 30
IDLE_MINUTES_ENV_VAR = "PDF_TOOLBOX_IDLE_MINUTES"


def idle_timeout_minutes(
    raw: str | None = None, default: float = DEFAULT_INACTIVITY_TIMEOUT_MINUTES
) -> float:
    """Read the idle timeout, in minutes, from the environment.

    Set PDF_TOOLBOX_IDLE_MINUTES to change it, or to 0 to never close automatically.
    Anything unreadable falls back to the default rather than disabling the timeout.
    """
    value = os.environ.get(IDLE_MINUTES_ENV_VAR) if raw is None else raw
    if value is None or not str(value).strip():
        return default
    try:
        minutes = float(value)
    except ValueError:
        return default
    return minutes if minutes >= 0 else default


INACTIVITY_TIMEOUT_MINUTES = idle_timeout_minutes()
# How long the countdown warning is shown before closing.
INACTIVITY_WARNING_SECONDS = 60

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {".txt"}
HTML_EXTENSIONS = {".html", ".htm"}
OFFICE_EXTENSIONS = {".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"}
SUPPORTED_INPUT_EXTENSIONS = (
    IMAGE_EXTENSIONS | PDF_EXTENSIONS | TEXT_EXTENSIONS | HTML_EXTENSIONS | OFFICE_EXTENSIONS
)

# Tool categories, in dashboard order.
CATEGORY_CONVERT_TO = "Convert to PDF"
CATEGORY_CONVERT_FROM = "Convert from PDF"
CATEGORY_ORGANIZE = "Organize"
CATEGORY_OPTIMIZE = "Optimize"
CATEGORY_EDIT = "Edit"
CATEGORY_SECURITY = "Security"

CATEGORIES = [
    CATEGORY_CONVERT_TO,
    CATEGORY_CONVERT_FROM,
    CATEGORY_ORGANIZE,
    CATEGORY_OPTIMIZE,
    CATEGORY_EDIT,
    CATEGORY_SECURITY,
]

# External dependency keys reported by the registry.
REQUIRES_LIBREOFFICE = "libreoffice"
REQUIRES_TESSERACT = "tesseract"

