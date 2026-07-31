"""Case-insensitive matching for option values coming from the GUI or CLI."""

from __future__ import annotations

from typing import Iterable


def match_choice(value: str | None, choices: Iterable[str], label: str) -> str:
    """Return the canonical choice matching value, or raise a friendly ValueError."""
    options = list(choices)
    text = (value or "").strip().lower()
    for choice in options:
        if choice.lower() == text:
            return choice
    allowed = ", ".join(options)
    raise ValueError(f"Choose {label}: {allowed}.")
