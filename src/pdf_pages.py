"""Page-level PDF organisation: rotate, extract, remove, reorder, insert."""

from __future__ import annotations

from pathlib import Path

from .output_paths import safe_output_path
from .pdf_tools import open_reader, parse_page_list, write_pdf, writer_with_metadata


def _parse_order(order_spec: str | None, page_count: int) -> list[int]:
    """Parse a full page order such as "3,1-2" into zero-based indexes."""
    if not order_spec or not order_spec.strip():
        raise ValueError("Enter the new page order, such as 3,1,2.")
    order = parse_page_list(order_spec, page_count)
    if len(order) != page_count:
        missing = sorted(index + 1 for index in range(page_count) if index not in order)
        raise ValueError(
            "The new order must list every page exactly once. "
            f"Missing page(s): {', '.join(str(number) for number in missing)}."
        )
    return order


def rotate_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    angle: int = 90,
    pages: str | None = None,
    password: str | None = None,
) -> Path:
    """Rotate selected pages clockwise. A blank page list rotates every page."""
    try:
        angle = int(angle)
    except (TypeError, ValueError) as exc:
        raise ValueError("Choose a rotation of 90, 180 or 270 degrees.") from exc
    if angle % 90 != 0 or angle % 360 == 0:
        raise ValueError("Choose a rotation of 90, 180 or 270 degrees.")

    source = Path(input_path)
    reader = open_reader(source, password)
    selected = set(parse_page_list(pages, len(reader.pages)))

    writer = writer_with_metadata(reader)
    for index, page in enumerate(reader.pages):
        if index in selected:
            page.rotate(angle % 360)
        writer.add_page(page)

    return write_pdf(writer, safe_output_path(output_dir, f"{source.stem}_rotated", ".pdf"))


def extract_pages(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    pages: str | None = None,
    separate_files: bool = False,
    password: str | None = None,
) -> list[Path]:
    """Copy selected pages into a new PDF, or into one PDF per page."""
    if not pages or not pages.strip():
        raise ValueError("Enter the pages to extract, such as 1-3,5.")

    source = Path(input_path)
    reader = open_reader(source, password)
    selected = parse_page_list(pages, len(reader.pages))

    if separate_files:
        outputs: list[Path] = []
        for index in selected:
            writer = writer_with_metadata(reader)
            writer.add_page(reader.pages[index])
            base = f"{source.stem}_page_{index + 1:03d}"
            outputs.append(write_pdf(writer, safe_output_path(output_dir, base, ".pdf")))
        return outputs

    writer = writer_with_metadata(reader)
    for index in selected:
        writer.add_page(reader.pages[index])
    output = write_pdf(writer, safe_output_path(output_dir, f"{source.stem}_extracted", ".pdf"))
    return [output]


def remove_pages(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    pages: str | None = None,
    password: str | None = None,
) -> Path:
    """Write a copy of the PDF without the selected pages."""
    if not pages or not pages.strip():
        raise ValueError("Enter the pages to remove, such as 2,5-6.")

    source = Path(input_path)
    reader = open_reader(source, password)
    page_count = len(reader.pages)
    removing = set(parse_page_list(pages, page_count))
    keeping = [index for index in range(page_count) if index not in removing]
    if not keeping:
        raise ValueError("Removing those pages would leave an empty PDF.")

    writer = writer_with_metadata(reader)
    for index in keeping:
        writer.add_page(reader.pages[index])

    return write_pdf(writer, safe_output_path(output_dir, f"{source.stem}_trimmed", ".pdf"))


def reorder_pages(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    order: str | None = None,
    password: str | None = None,
) -> Path:
    """Rebuild the PDF with pages in the given order."""
    source = Path(input_path)
    reader = open_reader(source, password)
    order_indexes = _parse_order(order, len(reader.pages))

    writer = writer_with_metadata(reader)
    for index in order_indexes:
        writer.add_page(reader.pages[index])

    return write_pdf(writer, safe_output_path(output_dir, f"{source.stem}_reordered", ".pdf"))


def apply_page_plan(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    plan: str = "",
    password: str | None = None,
) -> Path:
    """Rebuild a PDF from a page plan produced by the Organize workspace.

    The plan is a comma-separated list of `page` or `page:rotation` items, one per output
    page, in output order. Pages that are left out are dropped. Example: `3,1:90,2:180`.
    """
    if not plan or not plan.strip():
        raise ValueError("The page plan is empty, so there would be nothing to save.")

    source = Path(input_path)
    reader = open_reader(source, password)
    page_count = len(reader.pages)
    writer = writer_with_metadata(reader)

    for token in plan.split(","):
        item = token.strip()
        if not item:
            continue
        page_text, _, rotation_text = item.partition(":")
        try:
            number = int(page_text.strip())
            rotation = int(rotation_text.strip()) if rotation_text.strip() else 0
        except ValueError:
            raise ValueError("Page plan items must look like 3 or 3:90.") from None
        if number < 1 or number > page_count:
            raise ValueError(f"Page plan refers to page {number}, but the PDF has {page_count}.")
        if rotation % 90 != 0:
            raise ValueError("Page plan rotations must be 0, 90, 180 or 270.")

        page = reader.pages[number - 1]
        if rotation % 360:
            page.rotate(rotation % 360)
        writer.add_page(page)

    if not writer.pages:
        raise ValueError("The page plan kept no pages, so nothing was saved.")

    return write_pdf(writer, safe_output_path(output_dir, f"{source.stem}_organized", ".pdf"))


def insert_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    insert_file: str | Path | None = None,
    after_page: int = 0,
    password: str | None = None,
) -> Path:
    """Insert every page of another PDF after the given page number.

    Use after_page=0 to insert at the very beginning.
    """
    if not insert_file:
        raise ValueError("Choose the PDF file to insert.")
    insert_path = Path(insert_file).expanduser()
    if not insert_path.is_file():
        raise ValueError(f"File to insert was not found: {insert_path}")
    if insert_path.suffix.lower() != ".pdf":
        raise ValueError("The file to insert must be a PDF.")

    source = Path(input_path)
    reader = open_reader(source, password)
    extra = open_reader(insert_path, password)
    page_count = len(reader.pages)

    try:
        position = int(after_page)
    except (TypeError, ValueError) as exc:
        raise ValueError("Enter the insert position as a page number.") from exc
    if position < 0 or position > page_count:
        raise ValueError(f"Insert position must be between 0 and {page_count}.")

    writer = writer_with_metadata(reader)
    for index in range(position):
        writer.add_page(reader.pages[index])
    for page in extra.pages:
        writer.add_page(page)
    for index in range(position, page_count):
        writer.add_page(reader.pages[index])

    return write_pdf(writer, safe_output_path(output_dir, f"{source.stem}_combined", ".pdf"))
