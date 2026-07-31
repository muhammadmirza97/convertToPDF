"""Optional richer return value for tool processors."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ToolOutput:
    """Outputs plus an optional human-readable note, such as a size saving."""

    outputs: list[Path] = field(default_factory=list)
    note: str = ""


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
