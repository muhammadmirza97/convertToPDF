"""Local PDF security: password protection, unlocking and metadata removal."""

from __future__ import annotations

from pathlib import Path

import pikepdf

from .output_paths import safe_output_path
from .pdf_tools import ENCRYPTED_MESSAGE
from .tool_result import ToolOutput


def _open_pdf(source: Path, password: str | None) -> pikepdf.Pdf:
    try:
        return pikepdf.open(source, password=password or "")
    except pikepdf.PasswordError:
        if password:
            raise ValueError(f"The password for {source.name} is not correct.") from None
        raise ValueError(ENCRYPTED_MESSAGE.format(name=source.name)) from None
    except Exception as exc:
        raise ValueError(
            f"{source.name} could not be read as a PDF. Try Repair PDF first."
        ) from exc


def protect_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    new_password: str = "",
    confirm_password: str | None = None,
    owner_password: str = "",
    allow_printing: bool = True,
    allow_copying: bool = False,
    password: str | None = None,
) -> Path:
    """Write an AES-256 encrypted copy of the PDF."""
    new_password = (new_password or "").strip()
    if not new_password:
        raise ValueError("Enter the password to protect the PDF with.")
    if len(new_password) < 4:
        raise ValueError("Use a password of at least 4 characters.")
    if confirm_password is not None and confirm_password.strip() and confirm_password.strip() != new_password:
        raise ValueError("The two passwords do not match.")

    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_protected", ".pdf")
    permissions = pikepdf.Permissions(
        extract=bool(allow_copying),
        accessibility=True,
        modify_annotation=False,
        modify_assembly=False,
        modify_form=False,
        modify_other=False,
        print_lowres=bool(allow_printing),
        print_highres=bool(allow_printing),
    )
    encryption = pikepdf.Encryption(
        user=new_password,
        owner=(owner_password or "").strip() or new_password,
        R=6,
        allow=permissions,
    )

    pdf = _open_pdf(source, password)
    try:
        pdf.save(output_path, encryption=encryption)
    finally:
        pdf.close()
    return output_path


def unlock_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    password: str = "",
) -> Path:
    """Write a copy without encryption. Requires the correct password."""
    source = Path(input_path)
    if not (password or "").strip():
        raise ValueError(f"Enter the current password for {source.name}.")

    try:
        # Opening without a password tells us whether one is needed, and avoids
        # pikepdf's "a password was provided but none was needed" warning.
        with pikepdf.open(source) as probe:
            if not probe.is_encrypted:
                raise ValueError(f"{source.name} is not password protected.")
    except pikepdf.PasswordError:
        pass

    pdf = _open_pdf(source, password)
    try:
        output_path = safe_output_path(output_dir, f"{source.stem}_unlocked", ".pdf")
        pdf.save(output_path)
    finally:
        pdf.close()
    return output_path


def _metadata_summary(pdf: pikepdf.Pdf) -> list[str]:
    found = [f"{key.lstrip('/')}" for key in pdf.docinfo.keys()] if pdf.docinfo else []
    with pdf.open_metadata() as meta:
        if len(meta):
            found.append("XMP metadata")
    return found


def strip_metadata(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    password: str | None = None,
) -> ToolOutput:
    """Remove document information and XMP metadata from a copy of the PDF."""
    source = Path(input_path)
    output_path = safe_output_path(output_dir, f"{source.stem}_no_metadata", ".pdf")

    pdf = _open_pdf(source, password)
    try:
        removed = _metadata_summary(pdf)
        with pdf.open_metadata() as meta:
            for key in list(meta.keys()):
                del meta[key]
        if pdf.docinfo:
            for key in list(pdf.docinfo.keys()):
                del pdf.docinfo[key]
        pdf.save(output_path)
    finally:
        pdf.close()

    note = f"Removed: {', '.join(removed)}." if removed else "No metadata was present."
    return ToolOutput([output_path], note)


def read_metadata(input_path: str | Path, *, password: str | None = None) -> dict[str, str]:
    """Return document information fields for display."""
    source = Path(input_path)
    pdf = _open_pdf(source, password)
    try:
        return {str(key).lstrip("/"): str(value) for key, value in pdf.docinfo.items()}
    finally:
        pdf.close()
