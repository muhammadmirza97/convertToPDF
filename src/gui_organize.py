"""Visual Organize workspace: reorder, rotate and delete pages using thumbnails."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from .thumbnails import PageThumbnail, render_thumbnails


THUMB_EDGE = 150
COLUMNS = 5


@dataclass
class PlanItem:
    page_index: int      # zero-based index in the source PDF
    rotation: int = 0    # extra clockwise rotation in degrees


def plan_to_text(items: list[PlanItem]) -> str:
    """Render a plan in the format understood by pdf_pages.apply_page_plan."""
    parts = []
    for item in items:
        number = item.page_index + 1
        parts.append(f"{number}:{item.rotation % 360}" if item.rotation % 360 else str(number))
    return ",".join(parts)


class OrganizeWorkspace(ctk.CTkToplevel):
    """Modal window that builds a page plan for one PDF."""

    def __init__(self, parent, pdf_path: Path, *, password: str = "", on_apply=None) -> None:
        super().__init__(parent)
        self.title(f"Organize pages - {pdf_path.name}")
        self.geometry("1000x680")
        self.minsize(760, 520)

        self.pdf_path = pdf_path
        self.on_apply = on_apply
        self.thumbnails: list[PageThumbnail] = render_thumbnails(
            pdf_path, max_edge=THUMB_EDGE, password=password or None
        )
        self.images: dict[int, ctk.CTkImage] = {}
        self.items: list[PlanItem] = [PlanItem(thumb.index) for thumb in self.thumbnails]
        self.selected: set[int] = set()   # positions in self.items
        self.status = ctk.StringVar()

        self._build_ui()
        self._refresh()
        self.transient(parent)
        self.after(120, self._grab)

    def _grab(self) -> None:
        try:
            self.grab_set()
        except Exception:
            pass

    # --- layout -----------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(self, corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew")
        for column in range(8):
            bar.grid_columnconfigure(column, weight=0)
        bar.grid_columnconfigure(7, weight=1)

        buttons = [
            ("Select all", self._select_all),
            ("Select none", self._select_none),
            ("Rotate left", lambda: self._rotate(-90)),
            ("Rotate right", lambda: self._rotate(90)),
            ("Move left", lambda: self._move(-1)),
            ("Move right", lambda: self._move(1)),
            ("Delete", self._delete),
        ]
        for column, (text, command) in enumerate(buttons):
            ctk.CTkButton(bar, text=text, width=96, command=command).grid(
                row=0, column=column, padx=(10 if column == 0 else 4, 4), pady=10
            )

        self.grid_frame = ctk.CTkScrollableFrame(self, label_text="Click a page to select it")
        self.grid_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 4))
        for column in range(COLUMNS):
            self.grid_frame.grid_columnconfigure(column, weight=1)

        footer = ctk.CTkFrame(self, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, textvariable=self.status, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=12, pady=12
        )
        ctk.CTkButton(footer, text="Reset", width=90, command=self._reset).grid(
            row=0, column=1, padx=4, pady=12
        )
        ctk.CTkButton(footer, text="Cancel", width=90, command=self.destroy).grid(
            row=0, column=2, padx=4, pady=12
        )
        ctk.CTkButton(footer, text="Use this plan", width=130, command=self._apply).grid(
            row=0, column=3, padx=(4, 12), pady=12
        )

    # --- rendering --------------------------------------------------------

    def _image_for(self, item: PlanItem) -> ctk.CTkImage:
        key = item.page_index * 1000 + item.rotation % 360
        if key not in self.images:
            thumb = next(entry for entry in self.thumbnails if entry.index == item.page_index)
            image = thumb.to_image()
            if item.rotation % 360:
                # PIL rotates counter-clockwise, so negate to show a clockwise turn.
                image = image.rotate(-item.rotation % 360, expand=True)
            size = (image.width, image.height)
            self.images[key] = ctk.CTkImage(light_image=image, dark_image=image, size=size)
        return self.images[key]

    def _refresh(self) -> None:
        for child in self.grid_frame.winfo_children():
            child.destroy()

        for position, item in enumerate(self.items):
            selected = position in self.selected
            tile = ctk.CTkFrame(
                self.grid_frame,
                border_width=3 if selected else 1,
                border_color=("#1f6aa5", "#1f6aa5") if selected else ("gray70", "gray30"),
            )
            tile.grid(row=position // COLUMNS, column=position % COLUMNS, padx=8, pady=8, sticky="n")

            button = ctk.CTkButton(
                tile,
                image=self._image_for(item),
                text="",
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                width=THUMB_EDGE,
                height=THUMB_EDGE,
                command=lambda index=position: self._toggle(index),
            )
            button.grid(row=0, column=0, padx=6, pady=(6, 2))

            label = f"{position + 1}  (was page {item.page_index + 1})"
            if item.rotation % 360:
                label += f"  {item.rotation % 360} deg"
            ctk.CTkLabel(tile, text=label, font=ctk.CTkFont(size=11)).grid(
                row=1, column=0, padx=6, pady=(0, 6)
            )

        dropped = len(self.thumbnails) - len(self.items)
        message = f"{len(self.items)} page(s) in the plan"
        if dropped:
            message += f", {dropped} deleted"
        if self.selected:
            message += f", {len(self.selected)} selected"
        self.status.set(message)

    # --- actions ----------------------------------------------------------

    def _toggle(self, position: int) -> None:
        if position in self.selected:
            self.selected.discard(position)
        else:
            self.selected.add(position)
        self._refresh()

    def _select_all(self) -> None:
        self.selected = set(range(len(self.items)))
        self._refresh()

    def _select_none(self) -> None:
        self.selected.clear()
        self._refresh()

    def _targets(self) -> list[int]:
        return sorted(self.selected)

    def _rotate(self, degrees: int) -> None:
        targets = self._targets()
        if not targets:
            self.status.set("Select at least one page first.")
            return
        for position in targets:
            self.items[position].rotation = (self.items[position].rotation + degrees) % 360
        self._refresh()

    def _move(self, step: int) -> None:
        targets = self._targets()
        if not targets:
            self.status.set("Select at least one page first.")
            return
        order = targets if step < 0 else list(reversed(targets))
        moved: set[int] = set()
        for position in order:
            target = position + step
            if target < 0 or target >= len(self.items) or target in moved:
                moved.add(position)
                continue
            self.items[position], self.items[target] = self.items[target], self.items[position]
            moved.add(target)
            self.selected.discard(position)
            self.selected.add(target)
        self._refresh()

    def _delete(self) -> None:
        targets = self._targets()
        if not targets:
            self.status.set("Select at least one page first.")
            return
        if len(targets) >= len(self.items):
            self.status.set("Keep at least one page.")
            return
        for position in reversed(targets):
            del self.items[position]
        self.selected.clear()
        self._refresh()

    def _reset(self) -> None:
        self.items = [PlanItem(thumb.index) for thumb in self.thumbnails]
        self.selected.clear()
        self._refresh()

    def _apply(self) -> None:
        if not self.items:
            self.status.set("Keep at least one page.")
            return
        if self.on_apply:
            self.on_apply(plan_to_text(self.items))
        self.destroy()
