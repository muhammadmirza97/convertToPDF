"""Signature pad: draw a signature with the mouse and save it as a transparent PNG."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw

from .config import PROJECT_ROOT


SIGNATURE_DIR = PROJECT_ROOT / "output" / "signatures"
CANVAS_WIDTH = 640
CANVAS_HEIGHT = 220
INK_COLORS = {"Black": (10, 10, 10), "Blue": (20, 40, 140), "Dark gray": (70, 70, 70)}


class SignaturePad(ctk.CTkToplevel):
    """Modal window for drawing a signature by hand."""

    def __init__(self, parent, *, on_save=None) -> None:
        super().__init__(parent)
        self.title("Draw your signature")
        self.geometry("700x400")
        self.resizable(False, False)

        self.on_save = on_save
        self.strokes: list[list[tuple[int, int]]] = []
        self.current: list[tuple[int, int]] = []
        self.thickness = tk.IntVar(value=5)
        self.ink = tk.StringVar(value="Black")
        self.status = tk.StringVar(value="Draw with the mouse, then press Save.")

        self._build_ui()
        self.transient(parent)
        self.after(120, self._grab)

    def _grab(self) -> None:
        try:
            self.grab_set()
        except Exception:
            pass

    def _build_ui(self) -> None:
        controls = ctk.CTkFrame(self, corner_radius=0)
        controls.pack(fill="x")
        ctk.CTkLabel(controls, text="Ink").pack(side="left", padx=(12, 6), pady=10)
        ctk.CTkOptionMenu(controls, values=list(INK_COLORS), variable=self.ink, width=110).pack(
            side="left", pady=10
        )
        ctk.CTkLabel(controls, text="Thickness").pack(side="left", padx=(16, 6), pady=10)
        ctk.CTkSlider(controls, from_=2, to=12, number_of_steps=10, variable=self.thickness, width=140).pack(
            side="left", pady=10
        )
        ctk.CTkButton(controls, text="Clear", width=80, command=self._clear).pack(
            side="right", padx=12, pady=10
        )

        # A plain Tk canvas is used because CustomTkinter has no drawing surface.
        self.canvas = tk.Canvas(
            self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="white", highlightthickness=1
        )
        self.canvas.pack(padx=20, pady=12)
        self.canvas.bind("<ButtonPress-1>", self._start)
        self.canvas.bind("<B1-Motion>", self._draw)
        self.canvas.bind("<ButtonRelease-1>", self._end)

        footer = ctk.CTkFrame(self, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        ctk.CTkLabel(footer, textvariable=self.status, anchor="w").pack(
            side="left", padx=12, pady=12
        )
        ctk.CTkButton(footer, text="Save signature", width=140, command=self._save).pack(
            side="right", padx=12, pady=12
        )
        ctk.CTkButton(footer, text="Cancel", width=90, command=self.destroy).pack(
            side="right", pady=12
        )

    # --- drawing ----------------------------------------------------------

    def _start(self, event) -> None:
        self.current = [(event.x, event.y)]

    def _draw(self, event) -> None:
        if not self.current:
            return
        last = self.current[-1]
        self.canvas.create_line(
            last[0],
            last[1],
            event.x,
            event.y,
            width=self.thickness.get(),
            fill=self._hex_ink(),
            capstyle="round",
            smooth=True,
        )
        self.current.append((event.x, event.y))

    def _end(self, _event) -> None:
        if len(self.current) > 1:
            self.strokes.append(self.current)
        self.current = []

    def _hex_ink(self) -> str:
        red, green, blue = INK_COLORS[self.ink.get()]
        return f"#{red:02x}{green:02x}{blue:02x}"

    def _clear(self) -> None:
        self.canvas.delete("all")
        self.strokes = []
        self.current = []
        self.status.set("Cleared. Draw with the mouse, then press Save.")

    # --- saving -----------------------------------------------------------

    def render_png(self) -> Image.Image:
        """Draw the strokes onto a transparent image, trimmed to the ink."""
        image = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255, 0))
        pen = ImageDraw.Draw(image)
        color = INK_COLORS[self.ink.get()] + (255,)
        width = self.thickness.get()
        for stroke in self.strokes:
            pen.line(stroke, fill=color, width=width, joint="curve")
            for x, y in stroke:
                radius = width / 2
                pen.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

        box = image.getbbox()
        if box:
            pad = width
            box = (
                max(0, box[0] - pad),
                max(0, box[1] - pad),
                min(CANVAS_WIDTH, box[2] + pad),
                min(CANVAS_HEIGHT, box[3] + pad),
            )
            image = image.crop(box)
        return image

    def _save(self) -> None:
        if not self.strokes:
            self.status.set("Draw something first.")
            return
        SIGNATURE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = SIGNATURE_DIR / f"signature_{stamp}.png"
        self.render_png().save(target)
        if self.on_save:
            self.on_save(target)
        self.destroy()
