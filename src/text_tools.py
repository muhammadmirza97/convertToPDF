"""Plain text to PDF conversion."""

from __future__ import annotations

import textwrap
import json
import urllib.request
from pathlib import Path

import fitz
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .output_paths import safe_output_path


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def txt_to_pdf(input_path: str | Path, output_dir: str | Path) -> Path:
    source = Path(input_path)
    output_path = safe_output_path(output_dir, source.stem, ".pdf")
    text = _read_text(source)

    _page_width, page_height = letter
    margin = 54
    line_height = 14
    max_chars = 90
    y = page_height - margin

    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    pdf.setTitle(source.name)
    pdf.setFont("Helvetica", 11)

    for raw_line in text.splitlines() or [""]:
        wrapped = textwrap.wrap(
            raw_line,
            width=max_chars,
            replace_whitespace=False,
            drop_whitespace=False,
        ) or [""]
        for line in wrapped:
            if y < margin:
                pdf.showPage()
                pdf.setFont("Helvetica", 11)
                y = page_height - margin
            safe_line = line.encode("latin-1", errors="replace").decode("latin-1")
            pdf.drawString(margin, y, safe_line)
            y -= line_height

    pdf.save()
    return output_path


def pdf_to_markdown(input_path: str | Path, output_dir: str | Path) -> Path:
    """Convert PDF text to Markdown using font size, blocks, links, and tables."""
    source = Path(input_path)
    output = safe_output_path(output_dir, source.stem, ".md")
    chunks: list[str] = []
    with fitz.open(source) as document:
        for page_number, page in enumerate(document, start=1):
            if page_number > 1:
                chunks.append("\n---\n\n")
            sizes = [span["size"] for block in page.get_text("dict")["blocks"] if "lines" in block for line in block["lines"] for span in line["spans"]]
            body_size = sorted(sizes)[(len(sizes) - 1) // 2] if sizes else 11
            for block in page.get_text("dict", sort=True)["blocks"]:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    if not text:
                        continue
                    largest = max(span["size"] for span in line["spans"])
                    if largest >= body_size * 1.55:
                        text = f"# {text}"
                    elif largest >= body_size * 1.25:
                        text = f"## {text}"
                    elif text.startswith(("•", "·", "- ")):
                        text = "- " + text.lstrip("•·- ")
                    chunks.append(text + "\n\n")
            try:
                for table in page.find_tables().tables:
                    rows = table.extract()
                    if not rows:
                        continue
                    clean = [[str(cell or "").replace("|", "\\|") for cell in row] for row in rows]
                    chunks.append("| " + " | ".join(clean[0]) + " |\n")
                    chunks.append("| " + " | ".join("---" for _ in clean[0]) + " |\n")
                    for row in clean[1:]:
                        chunks.append("| " + " | ".join(row) + " |\n")
                    chunks.append("\n")
            except Exception:
                pass
            links = [link.get("uri") for link in page.get_links() if link.get("uri")]
            if links:
                chunks.append("Links:\n\n")
                chunks.extend(f"- [{uri}]({uri})\n" for uri in dict.fromkeys(links))
                chunks.append("\n")
    output.write_text("".join(chunks).strip() + "\n", encoding="utf-8")
    return output


def local_ai_process(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    task: str,
    enabled: bool = False,
    model: str = "llama3.2",
    target_language: str = "English",
) -> Path:
    """Summarize or translate through localhost Ollama only, when explicitly enabled."""
    if not enabled:
        raise RuntimeError("Local AI not enabled")
    source = Path(input_path)
    with fitz.open(source) as document:
        text = "\n".join(page.get_text() for page in document)
    if task == "summarize":
        prompt = "Summarize this PDF accurately and concisely:\n\n" + text
        suffix = "summary"
    elif task == "translate":
        prompt = f"Translate this PDF text to {target_language}. Preserve structure:\n\n{text}"
        suffix = "translated"
    else:
        raise ValueError("AI task must be summarize or translate.")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))["response"]
    except Exception as exc:
        raise RuntimeError(f"Local Ollama is unavailable: {exc}") from exc
    output = safe_output_path(output_dir, f"{source.stem}_{suffix}", ".md")
    output.write_text(result, encoding="utf-8")
    return output
