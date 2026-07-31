"""The registry of every tool the app offers.

This module is the single source of truth. The GUI, the CLI and validation all read it,
so adding a tool here makes it available everywhere without touching interface code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .config import (
    CATEGORY_CONVERT_FROM,
    CATEGORY_CONVERT_TO,
    CATEGORY_EDIT,
    CATEGORY_OPTIMIZE,
    CATEGORY_ORGANIZE,
    CATEGORY_SECURITY,
    HTML_EXTENSIONS,
    IMAGE_EXTENSIONS,
    OFFICE_EXTENSIONS,
    PDF_EXTENSIONS,
    REQUIRES_LIBREOFFICE,
    REQUIRES_TESSERACT,
    SUPPORTED_INPUT_EXTENSIONS,
    TEXT_EXTENSIONS,
)
from .ocr_tools import ocr_pdf
from .pdf_annotate import MARK_STYLES, SHAPES, add_image, add_shape, add_text, highlight_text
from .pdf_compare import COMPARE_MODES, compare_pdfs
from .pdf_export import EXCEL_MODES, pdf_to_excel, pdf_to_powerpoint
from .pdf_forms import FIELD_KINDS, create_form_field, fill_form, form_report
from .pdf_redact import redact_pdf
from .pdf_sign import PLACEMENTS, sign_pdf
from .html_tools import (
    ORIENTATIONS as HTML_ORIENTATIONS,
    PAGE_SIZES as HTML_PAGE_SIZES,
    html_to_pdf,
)
from .image_tools import FIT_MODES, ORIENTATIONS, PAGE_SIZES as IMAGE_PAGE_SIZES, images_to_pdf
from .office_tools import PDFA_VERSIONS, convert_office_to_pdf, pdf_to_pdfa, pdf_to_word
from .pdf_edit import COLORS, NUMBER_FORMATS, POSITIONS, add_page_numbers, crop_pdf, watermark_pdf
from .pdf_optimize import COMPRESSION_LEVELS, compress_pdf, repair_pdf
from .pdf_pages import (
    apply_page_plan,
    extract_pages,
    insert_pdf,
    remove_pages,
    reorder_pages,
    rotate_pdf,
)
from .pdf_security import protect_pdf, strip_metadata, unlock_pdf
from .pdf_tools import (
    extract_images,
    merge_pdfs,
    pdf_to_images,
    pdf_to_markdown,
    pdf_to_text,
    split_pdf,
)
from .text_tools import PAGE_SIZES as TEXT_PAGE_SIZES, txt_to_pdf


# Option kinds understood by the GUI form builder and the CLI.
KIND_TEXT = "text"
KIND_INT = "int"
KIND_FLOAT = "float"
KIND_CHOICE = "choice"
KIND_BOOL = "bool"
KIND_PASSWORD = "password"
KIND_FILE = "file"
# Like KIND_FILE, but the GUI also offers a pad for drawing a signature by hand.
KIND_SIGNATURE = "signature"


@dataclass(frozen=True)
class Option:
    """One user-adjustable setting for a tool."""

    key: str
    label: str
    kind: str
    default: Any = None
    choices: tuple[str, ...] = ()
    placeholder: str = ""
    help: str = ""

    def coerce(self, raw: Any) -> Any:
        """Convert a GUI string or CLI string into the value the processor expects."""
        if self.kind == KIND_BOOL:
            if isinstance(raw, bool):
                return raw
            return str(raw).strip().lower() in ("1", "true", "yes", "on")
        if raw is None:
            return self.default
        if isinstance(raw, str) and not raw.strip():
            if self.kind in (KIND_INT, KIND_FLOAT):
                return self.default
            if self.kind in (KIND_TEXT, KIND_PASSWORD, KIND_FILE, KIND_SIGNATURE):
                return ""
            return self.default
        if self.kind == KIND_INT:
            try:
                return int(str(raw).strip())
            except ValueError:
                raise ValueError(f"{self.label} must be a whole number.") from None
        if self.kind == KIND_FLOAT:
            try:
                return float(str(raw).strip())
            except ValueError:
                raise ValueError(f"{self.label} must be a number.") from None
        if self.kind == KIND_CHOICE:
            text = str(raw).strip()
            match = next((choice for choice in self.choices if choice.lower() == text.lower()), None)
            if match is None:
                allowed = ", ".join(self.choices)
                raise ValueError(f"{self.label} must be one of: {allowed}.")
            return match
        return str(raw)


@dataclass(frozen=True)
class Tool:
    """A single operation the user can run."""

    id: str
    label: str
    category: str
    description: str
    extensions: frozenset[str]
    processor: Callable[..., Any]
    batch: bool = True
    min_files: int = 1
    options: tuple[Option, ...] = ()
    requires: str | None = None
    # Optional hook for tools whose external dependency depends on the chosen files.
    requires_resolver: Callable[[list[Path]], str | None] | None = None
    # Shown instead of the generic dependency message when the dependency is missing.
    dependency_message: str = ""
    input_error: str = ""
    hint: str = ""
    # Name of an interactive GUI helper this tool offers, if any. See src/gui_organize.py.
    workspace: str = ""

    def resolve_requires(self, paths: list[Path]) -> str | None:
        """Return the dependency key these files actually need, if any."""
        if self.requires_resolver is not None:
            return self.requires_resolver(paths)
        return self.requires

    @property
    def accepts_label(self) -> str:
        return ", ".join(sorted(ext.lstrip(".").upper() for ext in self.extensions))

    def option(self, key: str) -> Option | None:
        return next((item for item in self.options if item.key == key), None)

    def defaults(self) -> dict[str, Any]:
        return {item.key: item.default for item in self.options}

    def coerce_options(self, raw: dict[str, Any] | None) -> dict[str, Any]:
        values = self.defaults()
        for key, value in (raw or {}).items():
            option = self.option(key)
            if option is None:
                continue
            values[key] = option.coerce(value)
        return values

    def rejects(self, paths: list[Path]) -> str:
        """Return an error message if the given files cannot be used, else ""."""
        if len(paths) < self.min_files:
            return self.input_error or f"{self.label} needs at least {self.min_files} file(s)."
        if any(path.suffix.lower() not in self.extensions for path in paths):
            return self.input_error or f"{self.label} needs {self.accepts_label} files."
        return ""


# --- Shared option definitions -------------------------------------------

PASSWORD_OPTION = Option(
    "password",
    "PDF password (if protected)",
    KIND_PASSWORD,
    default="",
    placeholder="leave blank if not protected",
    help="Only needed when the input PDF is password protected.",
)

PAGES_OPTION = Option(
    "pages",
    "Pages",
    KIND_TEXT,
    default="",
    placeholder="1-3,5 or blank for all",
    help="Blank means every page.",
)


def _pages_required(label: str, placeholder: str) -> Option:
    return Option(
        "pages",
        label,
        KIND_TEXT,
        default="",
        placeholder=placeholder,
        help="Use single pages and ranges, such as 1-3,5.",
    )


def _auto_to_pdf(path: Path, output_dir: Path, **options) -> Any:
    """Pick the right converter for one file based on its extension."""
    from .converter import auto_convert_one

    return auto_convert_one(path, output_dir, **options)


def _auto_requires(paths: list[Path]) -> str | None:
    """Auto convert only needs LibreOffice when every chosen file is an Office file."""
    if paths and all(path.suffix.lower() in OFFICE_EXTENSIONS for path in paths):
        return REQUIRES_LIBREOFFICE
    return None


TOOLS: tuple[Tool, ...] = (
    # --- Convert to PDF ---------------------------------------------------
    Tool(
        id="auto_to_pdf",
        label="Auto convert to PDF",
        category=CATEGORY_CONVERT_TO,
        description="Convert images, text, HTML and Office files to PDF, one PDF per file.",
        extensions=frozenset(SUPPORTED_INPUT_EXTENSIONS),
        processor=_auto_to_pdf,
        requires_resolver=_auto_requires,
        dependency_message="Office conversion needs LibreOffice. Other conversion tools still work.",
        input_error="Choose image, TXT, HTML or Office files.",
        hint="Mixed file types are fine. Each file becomes its own PDF.",
    ),
    Tool(
        id="images_to_pdf",
        label="Images to PDF",
        category=CATEGORY_CONVERT_TO,
        description="Turn JPG and PNG images into one PDF, or one PDF per image.",
        extensions=frozenset(IMAGE_EXTENSIONS),
        processor=images_to_pdf,
        batch=False,
        input_error="Choose one or more PNG/JPG/JPEG images.",
        options=(
            Option("single_file", "Combine into one PDF", KIND_BOOL, default=True),
            Option("page_size", "Page size", KIND_CHOICE, default="Match image size", choices=IMAGE_PAGE_SIZES),
            Option("orientation", "Orientation", KIND_CHOICE, default="Auto", choices=ORIENTATIONS),
            Option("fit", "Image fit", KIND_CHOICE, default="Fit inside page", choices=FIT_MODES),
            Option("margin_mm", "Margin (mm)", KIND_FLOAT, default=0.0),
        ),
        hint="Files are added in the order you selected them.",
    ),
    Tool(
        id="txt_to_pdf",
        label="TXT to PDF",
        category=CATEGORY_CONVERT_TO,
        description="Lay out plain text files as PDF pages.",
        extensions=frozenset(TEXT_EXTENSIONS),
        processor=txt_to_pdf,
        input_error="TXT to PDF needs text files.",
        options=(
            Option("font_size", "Font size", KIND_INT, default=11),
            Option("page_size", "Page size", KIND_CHOICE, default="Letter", choices=tuple(TEXT_PAGE_SIZES)),
            Option("orientation", "Orientation", KIND_CHOICE, default="Portrait", choices=("Portrait", "Landscape")),
            Option("margin_mm", "Margin (mm)", KIND_FLOAT, default=19.0),
        ),
    ),
    Tool(
        id="html_to_pdf",
        label="HTML to PDF",
        category=CATEGORY_CONVERT_TO,
        description="Render simple local HTML files as PDF. No JavaScript or remote assets.",
        extensions=frozenset(HTML_EXTENSIONS),
        processor=html_to_pdf,
        input_error="HTML to PDF needs .html or .htm files.",
        options=(
            Option("page_size", "Page size", KIND_CHOICE, default="A4", choices=HTML_PAGE_SIZES),
            Option("orientation", "Orientation", KIND_CHOICE, default="Portrait", choices=HTML_ORIENTATIONS),
            Option("margin_mm", "Margin (mm)", KIND_FLOAT, default=18.0),
        ),
        hint="Complex CSS layouts will not match a web browser.",
    ),
    Tool(
        id="office_to_pdf",
        label="Office to PDF",
        category=CATEGORY_CONVERT_TO,
        description="Convert Word, PowerPoint and Excel files with LibreOffice.",
        extensions=frozenset(OFFICE_EXTENSIONS),
        processor=convert_office_to_pdf,
        requires=REQUIRES_LIBREOFFICE,
        input_error="Office to PDF needs DOC/DOCX/PPT/PPTX/XLS/XLSX files.",
        hint="Layout may differ slightly from Microsoft Office.",
    ),
    # --- Convert from PDF -------------------------------------------------
    Tool(
        id="pdf_to_images",
        label="PDF to JPG or PNG",
        category=CATEGORY_CONVERT_FROM,
        description="Render PDF pages as image files.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=pdf_to_images,
        input_error="PDF to image needs PDF input files.",
        options=(
            Option("image_format", "Image format", KIND_CHOICE, default="png", choices=("png", "jpg")),
            Option("dpi", "Resolution (DPI)", KIND_INT, default=150, help="150 is good for screen, 300 for print."),
            Option("jpeg_quality", "JPG quality", KIND_INT, default=85),
            Option("grayscale", "Grayscale", KIND_BOOL, default=False),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
    ),
    Tool(
        id="extract_images",
        label="Extract images from PDF",
        category=CATEGORY_CONVERT_FROM,
        description="Save the pictures embedded in the PDF, without re-rendering the pages.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=extract_images,
        input_error="Extract images needs PDF input files.",
        options=(
            Option(
                "minimum_pixels",
                "Ignore images smaller than (pixels)",
                KIND_INT,
                default=64,
                help="Filters out icons, bullets and hairlines.",
            ),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="Images keep their original format and quality. Use PDF to JPG or PNG for whole pages.",
    ),
    Tool(
        id="pdf_to_text",
        label="PDF to text",
        category=CATEGORY_CONVERT_FROM,
        description="Extract the text layer of a PDF to a .txt file.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=pdf_to_text,
        input_error="PDF to text needs PDF input files.",
        options=(PAGES_OPTION, PASSWORD_OPTION),
        hint="Scanned PDFs have no text layer; OCR is not included yet.",
    ),
    Tool(
        id="pdf_to_markdown",
        label="PDF to Markdown",
        category=CATEGORY_CONVERT_FROM,
        description="Extract text as Markdown, guessing headings from font sizes.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=pdf_to_markdown,
        input_error="PDF to Markdown needs PDF input files.",
        options=(
            Option("page_breaks", "Add a rule between pages", KIND_BOOL, default=True),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="Best effort. Tables, columns and images are not reconstructed.",
    ),
    Tool(
        id="pdf_to_word",
        label="PDF to Word",
        category=CATEGORY_CONVERT_FROM,
        description="Convert a PDF to an editable .docx file with LibreOffice.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=pdf_to_word,
        requires=REQUIRES_LIBREOFFICE,
        input_error="PDF to Word needs PDF input files.",
        hint="Best effort. Complex layouts, columns and tables will need tidying up.",
    ),
    Tool(
        id="pdf_to_excel",
        label="PDF to Excel",
        category=CATEGORY_CONVERT_FROM,
        description="Write detected tables, or plain text lines, into an .xlsx workbook.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=pdf_to_excel,
        input_error="PDF to Excel needs PDF input files.",
        options=(
            Option("mode", "Content to export", KIND_CHOICE, default="Detected tables", choices=EXCEL_MODES),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="One worksheet per detected table. Merged cells and formatting are not kept.",
    ),
    Tool(
        id="pdf_to_powerpoint",
        label="PDF to PowerPoint",
        category=CATEGORY_CONVERT_FROM,
        description="Write one slide per PDF page, with the page text in the speaker notes.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=pdf_to_powerpoint,
        input_error="PDF to PowerPoint needs PDF input files.",
        options=(
            Option("dpi", "Slide image quality (DPI)", KIND_INT, default=150),
            Option("include_notes", "Put page text in speaker notes", KIND_BOOL, default=True),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="Each slide holds a picture of the page, so slide text is not directly editable.",
    ),
    Tool(
        id="pdf_to_pdfa",
        label="PDF to PDF/A",
        category=CATEGORY_CONVERT_FROM,
        description="Convert to the PDF/A archival format with LibreOffice.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=pdf_to_pdfa,
        requires=REQUIRES_LIBREOFFICE,
        input_error="PDF to PDF/A needs PDF input files.",
        options=(
            Option("version", "PDF/A version", KIND_CHOICE, default="PDF/A-2b", choices=tuple(PDFA_VERSIONS)),
        ),
        hint="PDF/A embeds fonts for long-term storage, so the file usually gets larger.",
    ),
    # --- Organize ---------------------------------------------------------
    Tool(
        id="merge_pdfs",
        label="Merge PDFs",
        category=CATEGORY_ORGANIZE,
        description="Join several PDFs into one, in the order you selected them.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=merge_pdfs,
        batch=False,
        min_files=2,
        input_error="Merge needs at least two PDF files.",
        options=(PASSWORD_OPTION,),
    ),
    Tool(
        id="split_pdf",
        label="Split PDF",
        category=CATEGORY_ORGANIZE,
        description="Split into one PDF per page, or one PDF per page range.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=split_pdf,
        input_error="Split needs PDF input files.",
        options=(
            Option(
                "page_ranges",
                "Ranges",
                KIND_TEXT,
                default="",
                placeholder="1-3,5 or blank for every page",
                help="Blank splits every page into its own PDF.",
            ),
            Option(
                "every_n_pages",
                "Or split into chunks of",
                KIND_INT,
                default=0,
                help="0 ignores this. 2 makes pages 1-2, 3-4, and so on.",
            ),
            PASSWORD_OPTION,
        ),
    ),
    Tool(
        id="rotate_pdf",
        label="Rotate pages",
        category=CATEGORY_ORGANIZE,
        description="Rotate selected pages clockwise.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=rotate_pdf,
        input_error="Rotate needs PDF input files.",
        options=(
            Option("angle", "Rotation", KIND_CHOICE, default="90", choices=("90", "180", "270")),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
    ),
    Tool(
        id="extract_pages",
        label="Extract pages",
        category=CATEGORY_ORGANIZE,
        description="Copy chosen pages into a new PDF.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=extract_pages,
        input_error="Extract needs PDF input files.",
        options=(
            _pages_required("Pages to keep", "1-3,5"),
            Option("separate_files", "One PDF per page", KIND_BOOL, default=False),
            PASSWORD_OPTION,
        ),
    ),
    Tool(
        id="remove_pages",
        label="Remove pages",
        category=CATEGORY_ORGANIZE,
        description="Write a copy of the PDF without the chosen pages.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=remove_pages,
        input_error="Remove pages needs PDF input files.",
        options=(_pages_required("Pages to remove", "2,5-6"), PASSWORD_OPTION),
    ),
    Tool(
        id="reorder_pages",
        label="Reorder pages",
        category=CATEGORY_ORGANIZE,
        description="Rebuild the PDF with pages in a new order.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=reorder_pages,
        input_error="Reorder needs PDF input files.",
        options=(
            Option(
                "order",
                "New page order",
                KIND_TEXT,
                default="",
                placeholder="3,1,2",
                help="List every page exactly once, such as 3,1-2.",
            ),
            PASSWORD_OPTION,
        ),
    ),
    Tool(
        id="insert_pdf",
        label="Insert pages from another PDF",
        category=CATEGORY_ORGANIZE,
        description="Insert every page of a second PDF at a chosen position.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=insert_pdf,
        input_error="Insert needs PDF input files.",
        options=(
            Option("insert_file", "PDF to insert", KIND_FILE, default="", placeholder="choose a PDF"),
            Option("after_page", "Insert after page", KIND_INT, default=0, help="0 inserts at the beginning."),
            PASSWORD_OPTION,
        ),
    ),
    Tool(
        id="organize_pdf",
        label="Organize pages visually",
        category=CATEGORY_ORGANIZE,
        description="Reorder, rotate and delete pages using thumbnails, then export.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=apply_page_plan,
        input_error="Organize needs PDF input files.",
        options=(
            Option(
                "plan",
                "Page plan",
                KIND_TEXT,
                default="",
                placeholder="3,1:90,2:180",
                help="One item per output page: page number, optionally :rotation.",
            ),
            PASSWORD_OPTION,
        ),
        workspace="organize",
        hint="Press Open workspace to build this plan with page thumbnails.",
    ),
    Tool(
        id="compare_pdfs",
        label="Compare two PDFs",
        category=CATEGORY_ORGANIZE,
        description="Report text differences and show changed pages side by side.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=compare_pdfs,
        batch=False,
        min_files=2,
        input_error="Compare needs exactly two PDF files: the old one, then the new one.",
        options=(
            Option("mode", "Comparison", KIND_CHOICE, default="Text and visual", choices=COMPARE_MODES),
            Option("dpi", "Visual resolution (DPI)", KIND_INT, default=100),
            PASSWORD_OPTION,
        ),
        hint="Select the older file first. Scanned pages need OCR before text can be compared.",
    ),
    # --- Optimize ---------------------------------------------------------
    Tool(
        id="compress_pdf",
        label="Compress PDF",
        category=CATEGORY_OPTIMIZE,
        description="Make a PDF smaller. Never produces a file larger than the original.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=compress_pdf,
        input_error="Compress needs PDF input files.",
        options=(
            Option("level", "Compression", KIND_CHOICE, default="Balanced", choices=COMPRESSION_LEVELS),
            PASSWORD_OPTION,
        ),
        hint="Balanced re-encodes images above 180 DPI down to 150 DPI. Low compression leaves images untouched.",
    ),
    Tool(
        id="repair_pdf",
        label="Repair PDF",
        category=CATEGORY_OPTIMIZE,
        description="Rebuild a damaged PDF structure so other tools can read it.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=repair_pdf,
        input_error="Repair needs PDF input files.",
        options=(PASSWORD_OPTION,),
        hint="Content that is already missing from the file cannot be recovered.",
    ),
    Tool(
        id="ocr_pdf",
        label="OCR PDF",
        category=CATEGORY_OPTIMIZE,
        description="Make a scanned PDF searchable by adding an invisible text layer.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=ocr_pdf,
        requires=REQUIRES_TESSERACT,
        input_error="OCR needs PDF input files.",
        options=(
            Option(
                "language",
                "Language",
                KIND_TEXT,
                default="eng",
                placeholder="eng, or eng+deu",
                help="Tesseract language codes, joined with + for more than one.",
            ),
            Option("dpi", "Scan resolution (DPI)", KIND_INT, default=300, help="300 suits most scans."),
            Option("skip_pages_with_text", "Skip pages that already have text", KIND_BOOL, default=True),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="The page image is kept exactly as it was; only a hidden text layer is added.",
    ),
    # --- Edit -------------------------------------------------------------
    Tool(
        id="watermark_pdf",
        label="Add watermark",
        category=CATEGORY_EDIT,
        description="Stamp text or an image across selected pages.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=watermark_pdf,
        input_error="Watermark needs PDF input files.",
        options=(
            Option("text", "Watermark text", KIND_TEXT, default="", placeholder="CONFIDENTIAL"),
            Option("image_file", "or watermark image", KIND_FILE, default="", placeholder="PNG or JPG"),
            Option("opacity", "Opacity (0.05-1.0)", KIND_FLOAT, default=0.25),
            Option("angle", "Angle (degrees)", KIND_INT, default=45),
            Option("font_size", "Text size", KIND_INT, default=48),
            Option("color", "Text colour", KIND_CHOICE, default="Gray", choices=tuple(COLORS)),
            Option("scale", "Image width (0.05-1.0 of page)", KIND_FLOAT, default=0.5),
            Option("tiled", "Repeat across the whole page", KIND_BOOL, default=False),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="Use text or an image, not both.",
    ),
    Tool(
        id="page_numbers",
        label="Add page numbers",
        category=CATEGORY_EDIT,
        description="Stamp page numbers onto selected pages.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=add_page_numbers,
        input_error="Page numbers needs PDF input files.",
        options=(
            Option("position", "Position", KIND_CHOICE, default="Bottom center", choices=POSITIONS),
            Option("number_format", "Format", KIND_CHOICE, default="Page 1", choices=tuple(NUMBER_FORMATS)),
            Option("start_number", "Start at", KIND_INT, default=1),
            Option("font_size", "Font size", KIND_INT, default=10),
            Option("color", "Colour", KIND_CHOICE, default="Black", choices=tuple(COLORS)),
            Option("margin_mm", "Margin (mm)", KIND_FLOAT, default=12.0),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
    ),
    Tool(
        id="crop_pdf",
        label="Crop pages",
        category=CATEGORY_EDIT,
        description="Trim margins from selected pages.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=crop_pdf,
        input_error="Crop needs PDF input files.",
        options=(
            Option("top_mm", "Trim top (mm)", KIND_FLOAT, default=0.0),
            Option("bottom_mm", "Trim bottom (mm)", KIND_FLOAT, default=0.0),
            Option("left_mm", "Trim left (mm)", KIND_FLOAT, default=0.0),
            Option("right_mm", "Trim right (mm)", KIND_FLOAT, default=0.0),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="Cropping hides content; it does not delete it. Use Redact PDF for removal.",
    ),
    Tool(
        id="highlight_text",
        label="Highlight or strike out text",
        category=CATEGORY_EDIT,
        description="Mark every occurrence of a phrase with a highlight, underline or strikeout.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=highlight_text,
        input_error="Highlighting needs PDF input files.",
        options=(
            Option("search_text", "Text to find", KIND_TEXT, default="", placeholder="invoice total"),
            Option("style", "Mark style", KIND_CHOICE, default="Highlight", choices=MARK_STYLES),
            Option("color", "Colour", KIND_CHOICE, default="Red", choices=tuple(COLORS)),
            Option("case_sensitive", "Match upper and lower case exactly", KIND_BOOL, default=False),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="Needs a text layer. Run OCR PDF first on scanned documents.",
    ),
    Tool(
        id="add_text",
        label="Add text",
        category=CATEGORY_EDIT,
        description="Draw a line or block of text at a chosen position.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=add_text,
        input_error="Adding text needs PDF input files.",
        options=(
            Option("text", "Text", KIND_TEXT, default="", placeholder="Approved on 1 August"),
            Option("x_mm", "From left (mm)", KIND_FLOAT, default=20.0),
            Option("y_mm", "From top (mm)", KIND_FLOAT, default=20.0),
            Option("font_size", "Font size", KIND_INT, default=12),
            Option("color", "Colour", KIND_CHOICE, default="Black", choices=tuple(COLORS)),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="Positions are millimetres from the top-left corner. Use \\n for a new line.",
    ),
    Tool(
        id="add_shape",
        label="Add shape",
        category=CATEGORY_EDIT,
        description="Draw a rectangle, ellipse, line or arrow on the page.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=add_shape,
        input_error="Adding a shape needs PDF input files.",
        options=(
            Option("shape", "Shape", KIND_CHOICE, default="Rectangle", choices=SHAPES),
            Option("x_mm", "From left (mm)", KIND_FLOAT, default=20.0),
            Option("y_mm", "From top (mm)", KIND_FLOAT, default=20.0),
            Option("width_mm", "Width (mm)", KIND_FLOAT, default=60.0),
            Option("height_mm", "Height (mm)", KIND_FLOAT, default=30.0),
            Option("line_width", "Line width", KIND_FLOAT, default=1.5),
            Option("color", "Colour", KIND_CHOICE, default="Red", choices=tuple(COLORS)),
            Option("fill", "Fill the shape", KIND_BOOL, default=False),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
    ),
    Tool(
        id="add_image",
        label="Add image",
        category=CATEGORY_EDIT,
        description="Place a PNG or JPG image at a chosen position and width.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=add_image,
        input_error="Adding an image needs PDF input files.",
        options=(
            Option("image_file", "Image", KIND_FILE, default="", placeholder="PNG or JPG"),
            Option("x_mm", "From left (mm)", KIND_FLOAT, default=20.0),
            Option("y_mm", "From top (mm)", KIND_FLOAT, default=20.0),
            Option("width_mm", "Width (mm)", KIND_FLOAT, default=50.0),
            Option("opacity", "Opacity (0.05-1.0)", KIND_FLOAT, default=1.0),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="Height follows the image's own proportions.",
    ),
    Tool(
        id="form_fields",
        label="List form fields",
        category=CATEGORY_EDIT,
        description="Write the PDF's fillable fields to a JSON file you can edit.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=form_report,
        input_error="Listing form fields needs PDF input files.",
        options=(PASSWORD_OPTION,),
        hint="Paste the edited JSON into Fill PDF form.",
    ),
    Tool(
        id="fill_form",
        label="Fill PDF form",
        category=CATEGORY_EDIT,
        description="Fill in an existing PDF form, and optionally lock the values.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=fill_form,
        input_error="Filling a form needs PDF input files.",
        options=(
            Option(
                "field_values",
                "Field values",
                KIND_TEXT,
                default="",
                placeholder='full_name=Mirza; agree=yes   or JSON',
                help="One name=value per item, or a JSON object.",
            ),
            Option("flatten", "Flatten (lock the values)", KIND_BOOL, default=False),
            PASSWORD_OPTION,
        ),
        workspace="form",
        hint="Press Open workspace to see the fields and type into them.",
    ),
    Tool(
        id="create_form_field",
        label="Create form field",
        category=CATEGORY_EDIT,
        description="Add a text box, checkbox or dropdown that can be filled later.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=create_form_field,
        input_error="Creating a form field needs PDF input files.",
        options=(
            Option("field_name", "Field name", KIND_TEXT, default="", placeholder="full_name"),
            Option("kind", "Field kind", KIND_CHOICE, default="Text box", choices=FIELD_KINDS),
            Option("x_mm", "From left (mm)", KIND_FLOAT, default=20.0),
            Option("y_mm", "From top (mm)", KIND_FLOAT, default=20.0),
            Option("width_mm", "Width (mm)", KIND_FLOAT, default=60.0),
            Option("height_mm", "Height (mm)", KIND_FLOAT, default=8.0),
            Option("initial_value", "Starting value", KIND_TEXT, default="", placeholder="optional"),
            Option(
                "choices",
                "Dropdown choices",
                KIND_TEXT,
                default="",
                placeholder="Yes, No, Maybe",
                help="Comma separated. Dropdowns only.",
            ),
            Option("border_color", "Border colour", KIND_CHOICE, default="Gray", choices=tuple(COLORS)),
            Option(
                "pages",
                "Pages",
                KIND_TEXT,
                default="",
                placeholder="blank = page 1 only",
                help="On several pages the name gets a number, so each field is separate.",
            ),
            PASSWORD_OPTION,
        ),
    ),
    # --- Security ---------------------------------------------------------
    Tool(
        id="protect_pdf",
        label="Protect with password",
        category=CATEGORY_SECURITY,
        description="Write an AES-256 encrypted copy of the PDF.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=protect_pdf,
        input_error="Protect needs PDF input files.",
        options=(
            Option("new_password", "New password", KIND_PASSWORD, default=""),
            Option("confirm_password", "Confirm password", KIND_PASSWORD, default=""),
            Option("allow_printing", "Allow printing", KIND_BOOL, default=True),
            Option("allow_copying", "Allow text copying", KIND_BOOL, default=False),
            PASSWORD_OPTION,
        ),
        hint="Keep the password safe. It cannot be recovered from the file.",
    ),
    Tool(
        id="unlock_pdf",
        label="Unlock PDF",
        category=CATEGORY_SECURITY,
        description="Remove encryption from a PDF you know the password for.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=unlock_pdf,
        input_error="Unlock needs PDF input files.",
        options=(Option("password", "Current password", KIND_PASSWORD, default=""),),
    ),
    Tool(
        id="strip_metadata",
        label="Remove metadata",
        category=CATEGORY_SECURITY,
        description="Strip author, title, software and XMP metadata from a copy.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=strip_metadata,
        input_error="Remove metadata needs PDF input files.",
        options=(PASSWORD_OPTION,),
    ),
    Tool(
        id="redact_pdf",
        label="Redact PDF",
        category=CATEGORY_SECURITY,
        description="Permanently remove text, chosen areas or images from the file.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=redact_pdf,
        input_error="Redact needs PDF input files.",
        options=(
            Option("search_text", "Text to remove", KIND_TEXT, default="", placeholder="account number"),
            Option(
                "areas",
                "Areas to remove",
                KIND_TEXT,
                default="",
                placeholder="1:20,30,80,10; 2:15,50,60,8",
                help="page:left,top,width,height in millimetres, separated by semicolons.",
            ),
            Option("remove_images", "Remove all images", KIND_BOOL, default=False),
            Option("case_sensitive", "Match upper and lower case exactly", KIND_BOOL, default=False),
            Option("fill_color", "Box colour", KIND_CHOICE, default="Black", choices=tuple(COLORS)),
            Option("replacement_text", "Replacement label", KIND_TEXT, default="", placeholder="REDACTED"),
            PAGES_OPTION,
            PASSWORD_OPTION,
        ),
        hint="Content is deleted from the file, not just covered. Check the result before sharing.",
    ),
    Tool(
        id="sign_pdf",
        label="Sign PDF",
        category=CATEGORY_SECURITY,
        description="Place a signature image, drawn or scanned, onto the page.",
        extensions=frozenset(PDF_EXTENSIONS),
        processor=sign_pdf,
        input_error="Signing needs PDF input files.",
        options=(
            Option(
                "signature_image",
                "Signature image",
                KIND_SIGNATURE,
                default="",
                placeholder="PNG or JPG, or draw one",
            ),
            Option("placement", "Position", KIND_CHOICE, default="Bottom right", choices=PLACEMENTS),
            Option("width_mm", "Signature width (mm)", KIND_FLOAT, default=45.0),
            Option("margin_mm", "Margin (mm)", KIND_FLOAT, default=15.0),
            Option("x_mm", "Custom from left (mm)", KIND_FLOAT, default=20.0),
            Option("y_mm", "Custom from top (mm)", KIND_FLOAT, default=240.0),
            Option("opacity", "Opacity (0.05-1.0)", KIND_FLOAT, default=1.0),
            Option("signed_by", "Name caption", KIND_TEXT, default="", placeholder="optional"),
            Option("sign_date", "Date caption", KIND_TEXT, default="", placeholder="optional"),
            Option(
                "pages",
                "Pages",
                KIND_TEXT,
                default="",
                placeholder="blank = last page only",
                help="Blank signs only the last page.",
            ),
            PASSWORD_OPTION,
        ),
        hint="A visible signature, like signing a printout. Not a certified digital signature.",
    ),
)

TOOLS_BY_ID: dict[str, Tool] = {tool.id: tool for tool in TOOLS}


def get_tool(tool_id: str) -> Tool:
    """Look up a tool by id, or by its display label."""
    if tool_id in TOOLS_BY_ID:
        return TOOLS_BY_ID[tool_id]

    match = next((tool for tool in TOOLS if tool.label.lower() == str(tool_id).strip().lower()), None)
    if match:
        return match
    raise ValueError(f"Unknown tool: {tool_id}")


def find_tool(tool_id: str) -> Tool | None:
    try:
        return get_tool(tool_id)
    except ValueError:
        return None


def tools_in_category(category: str, *, available_only: bool = False, missing: set[str] | None = None) -> list[Tool]:
    missing = missing or set()
    return [
        tool
        for tool in TOOLS
        if tool.category == category and not (available_only and tool.requires in missing)
    ]


def tools_for_extension(extension: str) -> list[Tool]:
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    return [tool for tool in TOOLS if ext in tool.extensions]
