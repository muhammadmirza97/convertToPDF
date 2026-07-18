"""Single source of truth for the iLovePDF-style tool grid."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    category: str
    description: str
    icon: str
    color: str
    action: str
    note: str = ""


TOOLS = [
    ToolDefinition("Merge PDF", "Organize PDF", "Combine multiple PDFs in the order you choose.", "M", "#ef4444", "Merge PDFs"),
    ToolDefinition("Split PDF", "Organize PDF", "Extract every page or selected page ranges.", "S", "#f97316", "Split PDF"),
    ToolDefinition("Organize PDF", "Organize PDF", "Reorder, delete, and insert PDF pages.", "O", "#8b5cf6", "Organize PDF"),
    ToolDefinition("Scan to PDF", "Organize PDF", "Import document photos into one PDF.", "SC", "#0ea5e9", "Images to single PDF"),
    ToolDefinition("Compress PDF", "Optimize PDF", "Reduce file size with low, medium, or high compression.", "C", "#22c55e", "Compress PDF"),
    ToolDefinition("Repair PDF", "Optimize PDF", "Rebuild damaged PDF structure and recover readable pages.", "R", "#14b8a6", "Repair PDF"),
    ToolDefinition("OCR PDF", "Optimize PDF", "Make scanned pages searchable with local Tesseract.", "OCR", "#06b6d4", "OCR PDF"),
    ToolDefinition("PDF to Word", "Convert PDF", "Extract text into an editable DOCX; layout is approximate.", "W", "#2563eb", "PDF to Word"),
    ToolDefinition("PDF to PowerPoint", "Convert PDF", "Create one editable slide per PDF page.", "P", "#ea580c", "PDF to PowerPoint"),
    ToolDefinition("PDF to Excel", "Convert PDF", "Extract detected tables into XLSX worksheets.", "X", "#16a34a", "PDF to Excel"),
    ToolDefinition("Word to PDF", "Convert PDF", "Convert Word documents using local LibreOffice.", "W", "#2563eb", "Office to PDF"),
    ToolDefinition("PowerPoint to PDF", "Convert PDF", "Convert presentations using local LibreOffice.", "P", "#ea580c", "Office to PDF"),
    ToolDefinition("Excel to PDF", "Convert PDF", "Convert spreadsheets using local LibreOffice.", "X", "#16a34a", "Office to PDF"),
    ToolDefinition("PDF to JPG", "Convert PDF", "Render every PDF page as a high-quality JPG.", "J", "#eab308", "PDF to JPG"),
    ToolDefinition("JPG to PDF", "Convert PDF", "Combine JPG or PNG images into a PDF.", "J", "#eab308", "Images to single PDF"),
    ToolDefinition("HTML to PDF", "Convert PDF", "Convert a local HTML file without accessing the web.", "H", "#7c3aed", "HTML to PDF"),
    ToolDefinition("PDF to PDF/A", "Convert PDF", "Create an archival PDF/A-1 copy with LibreOffice.", "A", "#dc2626", "PDF to PDF/A"),
    ToolDefinition("Edit PDF", "Edit PDF", "Place text, images, ink, and rectangles on a page.", "E", "#ec4899", "Edit PDF"),
    ToolDefinition("Watermark", "Edit PDF", "Overlay text or an image with position and opacity controls.", "WM", "#0f766e", "Watermark PDF"),
    ToolDefinition("Rotate", "Edit PDF", "Rotate all pages or selected ranges in a batch.", "RT", "#0284c7", "Rotate PDF"),
    ToolDefinition("Page numbers", "Edit PDF", "Add page numbers in six header or footer positions.", "#", "#4f46e5", "Page numbers"),
    ToolDefinition("Crop", "Edit PDF", "Set a true crop box on one page or the whole document.", "CR", "#db2777", "Crop PDF"),
    ToolDefinition("PDF Forms", "Edit PDF", "Fill existing fields or create text and checkbox fields.", "F", "#9333ea", "PDF Forms"),
    ToolDefinition("Sign", "PDF Security", "Draw or place an image signature; not cryptographic.", "SG", "#dc2626", "Sign PDF", "Image only - not a digital certificate."),
    ToolDefinition("Unlock", "PDF Security", "Remove encryption using the correct user password only.", "U", "#16a34a", "Unlock PDF"),
    ToolDefinition("Protect", "PDF Security", "Encrypt a PDF locally with AES-256.", "L", "#b91c1c", "Protect PDF"),
    ToolDefinition("Compare", "PDF Security", "Compare page text and export a unified diff report.", "CP", "#0369a1", "Compare PDF"),
    ToolDefinition("Redact", "PDF Security", "Permanently remove matched text or selected areas.", "RD", "#111827", "Redact PDF"),
    ToolDefinition("PDF to Markdown", "PDF Intelligence", "Preserve headings, lists, links, and detected tables.", "MD", "#334155", "PDF to Markdown"),
    ToolDefinition("AI Summarizer", "PDF Intelligence", "Summarize with explicitly enabled localhost Ollama.", "AI", "#7c3aed", "AI Summarizer"),
    ToolDefinition("Translate", "PDF Intelligence", "Translate with explicitly enabled localhost Ollama.", "TR", "#0891b2", "Translate"),
]

CATEGORIES = ["All", "Organize PDF", "Optimize PDF", "Convert PDF", "Edit PDF", "PDF Security", "PDF Intelligence"]

MEGA_MENU_GROUPS = [
    ("ORGANIZE PDF", ["Merge PDF", "Split PDF", "Organize PDF", "Scan to PDF"]),
    ("OPTIMIZE PDF", ["Compress PDF", "Repair PDF", "OCR PDF"]),
    ("CONVERT TO PDF", ["JPG to PDF", "Word to PDF", "PowerPoint to PDF", "Excel to PDF", "HTML to PDF"]),
    ("CONVERT FROM PDF", ["PDF to JPG", "PDF to Word", "PDF to PowerPoint", "PDF to Excel", "PDF to PDF/A"]),
    ("EDIT PDF", ["Rotate", "Page numbers", "Watermark", "Crop", "Edit PDF", "PDF Forms"]),
    ("PDF SECURITY", ["Unlock", "Protect", "Sign", "Redact", "Compare"]),
    ("PDF INTELLIGENCE", ["AI Summarizer", "Translate", "PDF to Markdown"]),
]
