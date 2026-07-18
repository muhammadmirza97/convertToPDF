"""CustomTkinter desktop GUI for Local PDF Converter."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
import json
import io
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import fitz
from PIL import Image, ImageDraw, ImageTk

from .config import (
    ACTION_AUTO,
    ACTION_SPLIT_PDF,
    ACTION_OFFICE_TO_PDF,
    ACTIONS,
    APP_NAME,
    DEFAULT_OUTPUT_DIR,
    get_inactivity_timeout_ms,
)
from .converter import convert_files
from .file_validation import detect_input_types, validate_action
from .logger import setup_logging
from .office_tools import find_libreoffice
from .pdf_tools import find_tesseract
from .output_paths import safe_output_path
from .ui.tool_catalog import CATEGORIES, MEGA_MENU_GROUPS, TOOLS, ToolDefinition


class LocalPDFConverterApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1240x820")
        self.minsize(960, 680)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color="#f7f7f8")

        self.logger = setup_logging()
        self.files: list[Path] = []
        self.output_folder = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.action = tk.StringVar(value=ACTION_AUTO)
        self.page_ranges = tk.StringVar(value="")
        self.status = tk.StringVar(value="Choose files, an output folder, and an action.")
        self.input_type = tk.StringVar(value="No files selected")
        self.libreoffice_path = find_libreoffice()
        self.tesseract_path = find_tesseract()
        self.current_tool: ToolDefinition | None = None
        self.option_vars: dict[str, tk.Variable] = {}
        self.organize_order: list[int] = []
        self.organize_insert_paths: list[Path] = []
        self._image_refs: list[object] = []
        self.signature_strokes: list[list[tuple[int, int]]] = []
        self._active_stroke: list[tuple[int, int]] | None = None
        self._preview_scale = (1.0, 1.0)
        self._drag_start: tuple[int, int] | None = None
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.is_converting = False
        self.inactivity_timeout_ms = get_inactivity_timeout_ms()
        self._inactivity_after_id: str | None = None
        self.logger.info("App startup. LibreOffice detected: %s", self.libreoffice_path or "not detected")

        self._build_ui()
        self._bind_activity_tracking()
        self._record_activity()
        self.after(100, self._drain_queue)

    def _bind_activity_tracking(self) -> None:
        for event_name in ("<Any-KeyPress>", "<Any-Button>", "<MouseWheel>", "<Motion>"):
            self.bind_all(event_name, self._record_activity, add="+")

    def _record_activity(self, _event: object | None = None) -> None:
        if self._inactivity_after_id is not None:
            self.after_cancel(self._inactivity_after_id)
        self._inactivity_after_id = self.after(self.inactivity_timeout_ms, self._close_for_inactivity)

    def _close_for_inactivity(self) -> None:
        self._inactivity_after_id = None
        if self.is_converting:
            self._record_activity()
            return
        self.logger.info(
            "App closed automatically after %s seconds of inactivity.",
            self.inactivity_timeout_ms // 1000,
        )
        self.destroy()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=0, height=78, border_width=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w", padx=28, pady=17)
        brand.bind("<Button-1>", lambda _event: self._show_home())
        heart = ctk.CTkLabel(brand, text="♥", text_color="#ed3330", font=ctk.CTkFont(size=30, weight="bold"))
        heart.grid(row=0, column=0, padx=(0, 7))
        logo = ctk.CTkLabel(brand, text="LOCAL PDF", text_color="#17171a", font=ctk.CTkFont(size=24, weight="bold"))
        logo.grid(row=0, column=1)
        for widget in (heart, logo):
            widget.bind("<Button-1>", lambda _event: self._show_home())
        nav = ctk.CTkFrame(header, fg_color="transparent")
        nav.grid(row=0, column=1, padx=22)
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for column, (label, action) in enumerate((("MERGE PDF", "Merge PDFs"), ("SPLIT PDF", "Split PDF"), ("COMPRESS PDF", "Compress PDF"))):
            button = ctk.CTkButton(nav, text=label, width=116, height=44, fg_color="transparent", hover_color="#f5f5f7", text_color="#1f1f22", font=ctk.CTkFont(size=13, weight="bold"), command=lambda a=action: self._open_action(a))
            button.grid(row=0, column=column, padx=3)
            self.nav_buttons[action] = button
        convert_menu = ctk.CTkOptionMenu(nav, values=[tool.name for tool in TOOLS if tool.category == "Convert PDF"], command=self._open_named_tool, width=148, height=44, fg_color="#ffffff", button_color="#ffffff", button_hover_color="#f5f5f7", text_color="#1f1f22", font=ctk.CTkFont(size=13, weight="bold"))
        convert_menu.set("CONVERT PDF")
        convert_menu.grid(row=0, column=3, padx=2)
        self.all_tools_button = ctk.CTkButton(nav, text="ALL PDF TOOLS  ⌄", width=170, height=44, fg_color="transparent", hover_color="#f5f5f7", text_color="#1f1f22", font=ctk.CTkFont(size=13, weight="bold"), command=self._toggle_mega_menu)
        self.all_tools_button.grid(row=0, column=4, padx=2)
        self.body = ctk.CTkFrame(self, fg_color="#f6f6fb", corner_radius=0, border_width=1, border_color="#e5e5ea")
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)
        self.mega_menu_visible = False
        self._build_mega_menu()
        self._show_home()

    def _build_mega_menu(self) -> None:
        self.mega_menu = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=15, border_width=1, border_color="#e1e1e7")
        for column_index in range(6):
            self.mega_menu.grid_columnconfigure(column_index, weight=1, uniform="mega")
        tools_by_name = {tool.name: tool for tool in TOOLS}
        for group_index, (heading, names) in enumerate(MEGA_MENU_GROUPS):
            column = group_index if group_index < 6 else 0
            row = 0 if group_index < 6 else 1
            group = ctk.CTkFrame(self.mega_menu, fg_color="transparent")
            group.grid(row=row, column=column, sticky="new", padx=18, pady=(20 if row == 0 else 5, 16))
            ctk.CTkLabel(group, text=heading, anchor="w", text_color="#777780", font=ctk.CTkFont(size=13, weight="bold")).pack(fill="x", pady=(0, 9))
            for name in names:
                tool = tools_by_name[name]
                reason = self._tool_disabled_reason(tool)
                label = f"{tool.icon}   {tool.name}" + ("  •" if reason else "")
                button = ctk.CTkButton(
                    group,
                    text=label,
                    anchor="w",
                    height=38,
                    corner_radius=8,
                    fg_color="transparent",
                    hover_color="#f1f1f6",
                    text_color="#33333a" if not reason else "#888890",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    command=lambda selected=tool: self._open_tool(selected),
                )
                button.pack(fill="x", pady=1)

    def _toggle_mega_menu(self) -> None:
        if self.mega_menu_visible:
            self._hide_mega_menu()
            return
        self.mega_menu.place(relx=0.5, y=82, anchor="n", relwidth=0.98, height=510)
        self.mega_menu.lift()
        self.mega_menu_visible = True
        self.all_tools_button.configure(text="ALL PDF TOOLS  ⌃", text_color="#ed3330")

    def _hide_mega_menu(self) -> None:
        if not getattr(self, "mega_menu_visible", False):
            return
        self.mega_menu.place_forget()
        self.mega_menu_visible = False
        self.all_tools_button.configure(text="ALL PDF TOOLS  ⌄", text_color="#1f1f22")

    def _clear_body(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()

    def _show_home(self, category: str = "All") -> None:
        if self.is_converting and self.current_tool is not None:
            return
        self._hide_mega_menu()
        self.current_tool = None
        self._update_nav_active(None)
        self._clear_body()
        page = ctk.CTkScrollableFrame(self.body, fg_color="#f6f6fb", corner_radius=0)
        page.grid(row=0, column=0, sticky="nsew")
        page.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(page, text="Every tool you need to work with PDFs in one place", text_color="#2e2e35", font=ctk.CTkFont(size=38, weight="bold")).grid(row=0, column=0, pady=(45, 9))
        subtitle = "Merge, split, compress, convert, edit and secure PDFs with a few clicks.\nEverything runs locally and your files stay on this computer."
        ctk.CTkLabel(page, text=subtitle, justify="center", text_color="#62626b", font=ctk.CTkFont(size=17)).grid(row=1, column=0, pady=(0, 28))
        pills = ctk.CTkFrame(page, fg_color="transparent")
        pills.grid(row=2, column=0, pady=(0, 25))
        for index, item in enumerate(CATEGORIES):
            selected = item == category
            ctk.CTkButton(pills, text=item, height=38, corner_radius=19, fg_color="#303039" if selected else "#ffffff", hover_color="#45454e" if selected else "#eeeeF3", text_color="#ffffff" if selected else "#4c4c55", border_width=0 if selected else 1, border_color="#d7d7df", font=ctk.CTkFont(size=13, weight="bold"), command=lambda value=item: self._show_home(value)).grid(row=0, column=index, padx=5)
        grid = ctk.CTkFrame(page, fg_color="transparent")
        grid.grid(row=3, column=0, sticky="ew", padx=27, pady=(0, 45))
        for column in range(5):
            grid.grid_columnconfigure(column, weight=1, uniform="cards")
        visible = [tool for tool in TOOLS if category == "All" or tool.category == category]
        for index, tool in enumerate(visible):
            self._create_tool_card(grid, tool, index // 5, index % 5)

    def _tool_disabled_reason(self, tool: ToolDefinition) -> str | None:
        if tool.action == "OCR PDF" and not self.tesseract_path:
            return "Tesseract not detected"
        if tool.action in {"Office to PDF", "PDF to PDF/A"} and not self.libreoffice_path:
            return "LibreOffice not detected"
        return None

    def _create_tool_card(self, parent: ctk.CTkFrame, tool: ToolDefinition, row: int, column: int) -> None:
        reason = self._tool_disabled_reason(tool)
        card = ctk.CTkFrame(parent, fg_color="#ffffff", corner_radius=13, border_width=1, border_color="#d9d9e1", height=225)
        card.grid(row=row, column=column, sticky="nsew", padx=7, pady=7)
        card.grid_propagate(False)
        icon = ctk.CTkLabel(card, text=tool.icon, width=48, height=48, corner_radius=9, fg_color=tool.color, text_color="#ffffff", font=ctk.CTkFont(size=14, weight="bold"))
        icon.place(x=20, y=22)
        name_label = ctk.CTkLabel(card, text=tool.name, anchor="w", text_color="#29292f", font=ctk.CTkFont(size=18, weight="bold"))
        name_label.place(x=20, y=88)
        description = tool.description + (f"\nUnavailable: {reason}." if reason else "")
        description_label = ctk.CTkLabel(card, text=description, anchor="nw", justify="left", wraplength=190, text_color="#74747d", font=ctk.CTkFont(size=13))
        description_label.place(x=20, y=126)
        for widget in (card, icon, name_label, description_label):
            widget.bind("<Button-1>", lambda _event, selected=tool: self._open_tool(selected))

    def _update_nav_active(self, action: str | None) -> None:
        for nav_action, button in getattr(self, "nav_buttons", {}).items():
            button.configure(text_color="#ed3330" if nav_action == action else "#1f1f22")

    def _open_action(self, action: str) -> None:
        tool = next(item for item in TOOLS if item.action == action)
        self._open_tool(tool)

    def _open_named_tool(self, name: str) -> None:
        tool = next(item for item in TOOLS if item.name == name)
        self._open_tool(tool)

    def _open_tool(self, tool: ToolDefinition) -> None:
        if self.is_converting:
            return
        self._hide_mega_menu()
        reason = self._tool_disabled_reason(tool)
        if reason:
            messagebox.showinfo(tool.name, f"{tool.name} is unavailable: {reason}.")
            return
        self.current_tool = tool
        self.action.set(tool.action)
        self.files = []
        self.option_vars = {}
        self.organize_order = []
        self.organize_insert_paths = []
        self._image_refs = []
        self.signature_strokes = []
        if hasattr(self, "redaction_rectangle"):
            del self.redaction_rectangle
        self.page_ranges.set("")
        self.status.set("Choose input files.")
        self._update_nav_active(tool.action)
        self._clear_body()
        tool_page = ctk.CTkFrame(self.body, fg_color="#f6f6fb", corner_radius=0)
        tool_page.grid(row=0, column=0, sticky="nsew")
        tool_page.grid_columnconfigure(0, weight=1)
        tool_page.grid_rowconfigure(3, weight=1)
        ctk.CTkButton(tool_page, text="←  All PDF tools", width=120, height=38, fg_color="transparent", hover_color="#ececf2", text_color="#4e4e57", font=ctk.CTkFont(size=13, weight="bold"), command=self._show_home).grid(row=0, column=0, sticky="w", padx=31, pady=(17, 0))
        ctk.CTkLabel(tool_page, text=tool.name, text_color="#303039", font=ctk.CTkFont(size=43, weight="bold")).grid(row=1, column=0, pady=(18, 5))
        description = tool.description + (f"  {tool.note}" if tool.note else "")
        ctk.CTkLabel(tool_page, text=description, wraplength=850, justify="center", text_color="#565661", font=ctk.CTkFont(size=19)).grid(row=2, column=0, pady=(0, 15))

        self.selection_stage = ctk.CTkFrame(tool_page, fg_color="transparent")
        self.selection_stage.grid(row=3, column=0, sticky="nsew")
        self.selection_stage.grid_columnconfigure(0, weight=1)
        self.hero_choose_button = ctk.CTkButton(
            self.selection_stage,
            text=self._selection_button_text(tool),
            width=470,
            height=112,
            corner_radius=13,
            fg_color="#ed3330",
            hover_color="#d92b28",
            text_color="#ffffff",
            font=ctk.CTkFont(size=27, weight="bold"),
            command=self._choose_files,
        )
        self.hero_choose_button.grid(row=0, column=0, pady=(38, 12))
        ctk.CTkLabel(self.selection_stage, text="Choose files stored on this computer", text_color="#64646d", font=ctk.CTkFont(size=14)).grid(row=1, column=0)
        ctk.CTkLabel(self.selection_stage, text="100% offline  •  no uploads  •  no account", text_color="#9898a0", font=ctk.CTkFont(size=12)).grid(row=2, column=0, pady=(12, 0))

        self.workspace_panel = ctk.CTkFrame(tool_page, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#dedee6")
        self.workspace_panel.grid(row=3, column=0, sticky="nsew", padx=55, pady=(15, 22))
        self.workspace_panel.grid_columnconfigure(0, weight=1)
        self.workspace_panel.grid_rowconfigure(2, weight=1)
        self.workspace_panel.grid_remove()

        controls = ctk.CTkFrame(self.workspace_panel, fg_color="#fafafa", corner_radius=12)
        controls.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 7))
        controls.grid_columnconfigure(1, weight=1)
        self.choose_button = ctk.CTkButton(controls, text="Change files", width=110, fg_color="#ed3330", hover_color="#d92b28", command=self._choose_files)
        self.choose_button.grid(row=0, column=0, padx=12, pady=12)
        self.file_count_label = ctk.CTkLabel(controls, text="0 files", anchor="w", text_color="#3e3e46", font=ctk.CTkFont(size=14, weight="bold"))
        self.file_count_label.grid(row=0, column=1, sticky="ew")
        self.output_button = ctk.CTkButton(controls, text="Output folder", width=115, fg_color="#3b3b43", hover_color="#292930", command=self._choose_output)
        self.output_button.grid(row=0, column=2, padx=12)
        self.output_entry = ctk.CTkEntry(controls, textvariable=self.output_folder, width=275, height=38, border_color="#d8d8df")
        self.output_entry.grid(row=0, column=3, padx=(0, 12))
        self.output_entry.bind("<KeyRelease>", lambda _event: self._validate())
        self.options_frame = ctk.CTkFrame(self.workspace_panel, fg_color="transparent")
        self.options_frame.grid(row=1, column=0, sticky="ew", padx=23, pady=8)
        self._build_options(tool.action)
        self.log_box = ctk.CTkTextbox(self.workspace_panel, wrap="word", height=105, fg_color="#f8f8fa", border_width=1, border_color="#e1e1e7")
        self.log_box.grid(row=2, column=0, sticky="nsew", padx=23, pady=8)
        self.log_box.insert("end", "Conversion log will appear here.\n")
        self.log_box.configure(state="disabled")
        footer = ctk.CTkFrame(self.workspace_panel, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=23, pady=(6, 20))
        footer.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(footer, textvariable=self.status, anchor="w", text_color="#55555f")
        self.status_label.grid(row=0, column=0, sticky="ew")
        self.progress = ctk.CTkProgressBar(footer, progress_color="#e5322d")
        self.progress.grid(row=1, column=0, sticky="ew", padx=(0, 15), pady=8)
        self.progress.set(0)
        self.convert_button = ctk.CTkButton(footer, text="Run tool", width=170, height=52, corner_radius=10, fg_color="#ed3330", hover_color="#d92b28", font=ctk.CTkFont(size=17, weight="bold"), command=self._start_conversion)
        self.convert_button.grid(row=0, column=1, rowspan=2)
        ctk.CTkLabel(tool_page, text="© Local PDF  •  Offline PDF toolkit", text_color="#777780", font=ctk.CTkFont(size=11)).grid(row=4, column=0, sticky="w", padx=28, pady=(0, 12))
        self._validate()

    @staticmethod
    def _selection_button_text(tool: ToolDefinition) -> str:
        if tool.action in {"Images to single PDF"}:
            return "Select image files"
        if tool.action == "Office to PDF":
            return "Select Office files"
        if tool.action == "HTML to PDF":
            return "Select HTML file"
        if tool.action in {"Merge PDFs", "Compare PDF"}:
            return "Select PDF files"
        return "Select PDF file"

    def _add_option_entry(self, label: str, key: str, default: str = "", placeholder: str = "") -> None:
        column = len(self.option_vars)
        variable = tk.StringVar(value=default)
        self.option_vars[key] = variable
        block = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        block.grid(row=0, column=column, sticky="ew", padx=5)
        ctk.CTkLabel(block, text=label, anchor="w", text_color="#555555").pack(fill="x")
        ctk.CTkEntry(block, textvariable=variable, placeholder_text=placeholder, width=155).pack(fill="x")

    def _add_option_menu(self, label: str, key: str, values: list[str], default: str) -> None:
        column = len(self.option_vars)
        variable = tk.StringVar(value=default)
        self.option_vars[key] = variable
        block = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        block.grid(row=0, column=column, sticky="ew", padx=5)
        ctk.CTkLabel(block, text=label, anchor="w", text_color="#555555").pack(fill="x")
        ctk.CTkOptionMenu(block, variable=variable, values=values, width=155).pack(fill="x")

    def _build_options(self, action: str) -> None:
        if action in {ACTION_SPLIT_PDF, "Rotate PDF"}:
            self._add_option_entry("Pages", "page_ranges", "", "1-3,5 or blank")
        if action == "Rotate PDF":
            self._add_option_menu("Rotation", "degrees", ["90", "180", "270"], "90")
        elif action == "Compress PDF":
            self._add_option_menu("Compression", "preset", ["low", "medium", "high"], "medium")
        elif action == "PDF to JPG":
            self._add_option_entry("JPG quality", "jpeg_quality", "90")
        elif action == "OCR PDF":
            self._add_option_entry("Language", "language", "eng")
        elif action == "Organize PDF":
            ctk.CTkButton(self.options_frame, text="Insert PDF pages", command=self._choose_insert_pdfs).grid(row=0, column=0, padx=5, pady=(20, 0))
            self.organize_preview = ctk.CTkScrollableFrame(self.options_frame, orientation="horizontal", height=170, fg_color="#f5f5f5")
            self.organize_preview.grid(row=1, column=0, columnspan=8, sticky="ew", pady=(8, 0))
        elif action == "Edit PDF":
            self._add_option_entry("Text to add", "text", "")
            self._add_option_entry("Page", "page_number", "1")
            self._add_option_entry("Position X,Y", "point", "72,72")
            self._add_page_preview("click")
        elif action == "Watermark PDF":
            self._add_option_entry("Watermark text", "text", "CONFIDENTIAL")
            self._add_option_menu("Position", "position", ["top-left", "top", "top-right", "left", "center", "right", "bottom-left", "bottom", "bottom-right"], "center")
            self._add_option_menu("Rotation", "rotation", ["0", "90", "180", "270"], "0")
            self._add_option_entry("Opacity", "opacity", "0.25")
            self._add_option_entry("Image (optional)", "image_path", "", "Local PNG/JPG path")
        elif action == "Page numbers":
            self._add_option_menu("Position", "position", ["top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right"], "bottom-center")
            self._add_option_entry("Start", "start_number", "1")
            total = tk.BooleanVar(value=False)
            self.option_vars["include_total"] = total
            ctk.CTkCheckBox(self.options_frame, text="n of N", variable=total).grid(row=0, column=len(self.option_vars), padx=12, pady=(22, 0))
        elif action == "Crop PDF":
            self._add_option_entry("Crop box x0,y0,x1,y1", "rect", "36,36,559,806")
            self._add_page_preview("crop")
        elif action in {"Protect PDF", "Unlock PDF"}:
            self._add_option_entry("Password", "password", "")
        elif action == "Redact PDF":
            self._add_option_entry("Text to remove", "search_text", "")
            self._add_page_preview("redact")
        elif action == "PDF Forms":
            self._add_option_menu("Mode", "form_mode", ["fill", "create text", "create checkbox"], "fill")
            self._add_option_entry("Field values (JSON)", "values", "{}", '{"name":"Ada"}')
            self._add_option_entry("New field name", "field_name", "field1")
            self._add_option_entry("Field box", "rect", "72,150,260,180")
        elif action == "Sign PDF":
            self._add_option_entry("Signature PNG/JPG", "signature_image", "", "Local image path")
            self._add_option_entry("Page", "page_number", "1")
            self._add_option_entry("Box x0,y0,x1,y1", "rect", "72,650,220,720")
            self.signature_canvas = tk.Canvas(self.options_frame, width=360, height=90, bg="white", highlightthickness=1, highlightbackground="#cccccc")
            self.signature_canvas.grid(row=1, column=0, columnspan=5, pady=(8, 0))
            self.signature_canvas.bind("<ButtonPress-1>", self._signature_start)
            self.signature_canvas.bind("<B1-Motion>", self._signature_drag)
        elif action in {"AI Summarizer", "Translate"}:
            enabled = tk.BooleanVar(value=False)
            self.option_vars["enabled"] = enabled
            ctk.CTkCheckBox(self.options_frame, text="Enable localhost Ollama", variable=enabled).grid(row=0, column=0, padx=8, pady=(22, 0))
            self._add_option_entry("Ollama model", "model", "llama3.2")
            if action == "Translate":
                self._add_option_entry("Target language", "target_language", "English")

    def _add_page_preview(self, mode: str) -> None:
        self.preview_mode = mode
        self.preview_canvas = tk.Canvas(self.options_frame, width=420, height=230, bg="#eeeeee", highlightthickness=1, highlightbackground="#cccccc")
        self.preview_canvas.grid(row=1, column=0, columnspan=8, pady=(10, 0))
        if mode == "click":
            self.preview_canvas.bind("<Button-1>", self._preview_click)
        else:
            self.preview_canvas.bind("<ButtonPress-1>", self._preview_drag_start)
            self.preview_canvas.bind("<B1-Motion>", self._preview_drag_move)
            self.preview_canvas.bind("<ButtonRelease-1>", self._preview_drag_end)

    def _choose_insert_pdfs(self) -> None:
        selected = filedialog.askopenfilenames(title="Insert PDF pages", filetypes=[("PDF files", "*.pdf")])
        if selected:
            self.organize_insert_paths.extend(Path(path) for path in selected)
            self._write_log(f"Will append pages from {len(selected)} PDF(s).")

    def _load_organize_thumbnails(self) -> None:
        if not self.files:
            return
        with fitz.open(self.files[0]) as document:
            if not self.organize_order:
                self.organize_order = list(range(len(document)))
        self._render_organize_thumbnails()

    def _render_organize_thumbnails(self) -> None:
        for child in self.organize_preview.winfo_children():
            child.destroy()
        self._image_refs = []
        with fitz.open(self.files[0]) as document:
            for position, page_index in enumerate(self.organize_order):
                page = document[page_index]
                pixmap = page.get_pixmap(matrix=fitz.Matrix(0.18, 0.18), alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                display = ctk.CTkImage(light_image=image, size=image.size)
                self._image_refs.append(display)
                tile = ctk.CTkFrame(self.organize_preview, fg_color="#ffffff")
                tile.grid(row=0, column=position, padx=5, pady=5)
                ctk.CTkLabel(tile, text=f"Page {page_index + 1}", image=display, compound="top").grid(row=0, column=0, columnspan=3, padx=5, pady=5)
                ctk.CTkButton(tile, text="↑", width=30, command=lambda p=position: self._move_organize_page(p, -1)).grid(row=1, column=0, padx=2, pady=3)
                ctk.CTkButton(tile, text="↓", width=30, command=lambda p=position: self._move_organize_page(p, 1)).grid(row=1, column=1, padx=2, pady=3)
                ctk.CTkButton(tile, text="×", width=30, fg_color="#e5322d", command=lambda p=position: self._delete_organize_page(p)).grid(row=1, column=2, padx=2, pady=3)

    def _move_organize_page(self, position: int, delta: int) -> None:
        target = position + delta
        if 0 <= target < len(self.organize_order):
            self.organize_order[position], self.organize_order[target] = self.organize_order[target], self.organize_order[position]
            self._render_organize_thumbnails()

    def _delete_organize_page(self, position: int) -> None:
        if len(self.organize_order) > 1:
            self.organize_order.pop(position)
            self._render_organize_thumbnails()

    def _load_page_preview(self) -> None:
        if not self.files or not hasattr(self, "preview_canvas"):
            return
        with fitz.open(self.files[0]) as document:
            page = document[0]
            scale = min(420 / page.rect.width, 230 / page.rect.height)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            photo = ImageTk.PhotoImage(image)
            self._image_refs = [photo]
            self._preview_scale = (page.rect.width / image.width, page.rect.height / image.height)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(0, 0, image=photo, anchor="nw")

    def _preview_click(self, event: tk.Event) -> None:
        x = event.x * self._preview_scale[0]
        y = event.y * self._preview_scale[1]
        variable = self.option_vars.get("point")
        if variable:
            variable.set(f"{x:.1f},{y:.1f}")

    def _preview_drag_start(self, event: tk.Event) -> None:
        self._drag_start = (event.x, event.y)

    def _preview_drag_move(self, event: tk.Event) -> None:
        if self._drag_start:
            self.preview_canvas.delete("selection")
            self.preview_canvas.create_rectangle(*self._drag_start, event.x, event.y, outline="#e5322d", width=2, tags="selection")

    def _preview_drag_end(self, event: tk.Event) -> None:
        if not self._drag_start:
            return
        x0, y0 = self._drag_start
        x1, y1 = event.x, event.y
        rect = (min(x0, x1) * self._preview_scale[0], min(y0, y1) * self._preview_scale[1], max(x0, x1) * self._preview_scale[0], max(y0, y1) * self._preview_scale[1])
        if self.preview_mode == "crop":
            self.option_vars["rect"].set(",".join(f"{value:.1f}" for value in rect))
        else:
            self.redaction_rectangle = rect
        self._drag_start = None

    def _signature_start(self, event: tk.Event) -> None:
        self._active_stroke = [(event.x, event.y)]
        self.signature_strokes.append(self._active_stroke)

    def _signature_drag(self, event: tk.Event) -> None:
        if self._active_stroke:
            previous = self._active_stroke[-1]
            self._active_stroke.append((event.x, event.y))
            self.signature_canvas.create_line(*previous, event.x, event.y, fill="black", width=3, capstyle="round", smooth=True)

    @staticmethod
    def _number_list(value: str, cast: type = float) -> tuple[object, ...]:
        return tuple(cast(item.strip()) for item in value.split(",") if item.strip())

    def _collect_options(self) -> tuple[str | None, dict[str, object]]:
        raw = {key: variable.get() for key, variable in self.option_vars.items()}
        pages = str(raw.pop("page_ranges", "")).strip() or None
        action = self.action.get()
        if action == "Organize PDF":
            raw["page_order"] = list(self.organize_order) if self.organize_order else None
            raw["insert_paths"] = list(self.organize_insert_paths)
        for key in ("degrees", "jpeg_quality", "rotation", "start_number", "page_number"):
            if key in raw:
                raw[key] = int(str(raw[key]))
        if "opacity" in raw:
            raw["opacity"] = float(str(raw["opacity"]))
        for key in ("point", "rect"):
            if key in raw:
                raw[key] = self._number_list(str(raw[key]), float)
        if action == "PDF Forms":
            mode = str(raw.pop("form_mode"))
            if mode == "fill":
                raw["values"] = json.loads(str(raw["values"]))
                raw.pop("field_name", None)
                raw.pop("rect", None)
            else:
                raw.pop("values", None)
                raw["checkbox"] = mode == "create checkbox"
        if action == "Watermark PDF" and not str(raw.get("image_path", "")).strip():
            raw.pop("image_path", None)
        if action == "Redact PDF" and hasattr(self, "redaction_rectangle"):
            raw["rectangles"] = [self.redaction_rectangle]
        if action == "Sign PDF" and not str(raw.get("signature_image", "")).strip():
            if not self.signature_strokes:
                raise ValueError("Draw a signature or choose a signature image.")
            signature = Image.new("RGBA", (360, 90), (255, 255, 255, 0))
            draw = ImageDraw.Draw(signature)
            for stroke in self.signature_strokes:
                if len(stroke) > 1:
                    draw.line(stroke, fill=(0, 0, 0, 255), width=3, joint="curve")
            signature_path = safe_output_path(self.output_folder.get(), "drawn_signature", ".png")
            signature.save(signature_path)
            raw["signature_image"] = str(signature_path)
        return pages, raw

    def _choose_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title=self._selection_button_text(self.current_tool) if self.current_tool else "Select files",
            initialdir=str(Path.cwd()),
            filetypes=self._file_dialog_types(),
        )
        if selected:
            self.files = [Path(path) for path in selected]
            self.file_count_label.configure(text=f"{len(self.files)} file(s) selected")
            self._write_log(f"Selected {len(self.files)} file(s).")
            self.selection_stage.grid_remove()
            self.workspace_panel.grid()
            if self.action.get() == "Organize PDF":
                self.organize_order = []
                self._load_organize_thumbnails()
            elif self.action.get() in {"Edit PDF", "Crop PDF", "Redact PDF"}:
                self._load_page_preview()
            self._validate()

    def _file_dialog_types(self) -> list[tuple[str, str]]:
        action = self.action.get()
        if action == "Images to single PDF":
            return [("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        if action == "Office to PDF":
            return [("Office files", "*.docx *.doc *.pptx *.ppt *.xlsx *.xls"), ("All files", "*.*")]
        if action == "HTML to PDF":
            return [("HTML files", "*.html *.htm"), ("All files", "*.*")]
        return [("PDF files", "*.pdf"), ("All files", "*.*")]

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(title="Choose output folder", initialdir=self.output_folder.get())
        if selected:
            self.output_folder.set(selected)
            self._write_log(f"Output folder: {selected}")
            self._validate()

    def _validate(self) -> None:
        if self.is_converting:
            self.convert_button.configure(state="disabled")
            return

        if self.files:
            input_types = ", ".join(sorted(detect_input_types(self.files)))
            self.input_type.set(f"Detected input: {input_types}")
        else:
            self.input_type.set("No files selected")

        action = self.action.get()

        result = validate_action(
            self.files,
            self.output_folder.get(),
            action,
            libreoffice_available=self.libreoffice_path is not None,
        )
        self.status.set(result.message)
        self.convert_button.configure(state="normal" if result.ok else "disabled")

        if action == ACTION_OFFICE_TO_PDF and self.libreoffice_path is None:
            self.status.set("LibreOffice was not found. Office conversion is unavailable.")
            self.convert_button.configure(state="disabled")

    def _start_conversion(self) -> None:
        self._record_activity()
        files = list(self.files)
        output = self.output_folder.get()
        action = self.action.get()
        try:
            pages, options = self._collect_options()
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_NAME, f"Check the tool options: {exc}")
            return
        self.is_converting = True
        self.convert_button.configure(state="disabled")
        self.choose_button.configure(state="disabled")
        self.output_button.configure(state="disabled")
        self.progress.set(0)
        self.status.set("Starting conversion...")
        self._write_log(f"Starting conversion: {action}.")

        thread = threading.Thread(
            target=self._run_conversion,
            args=(files, output, action, pages, options),
            daemon=True,
        )
        thread.start()

    def _run_conversion(
        self,
        files: list[Path],
        output: str,
        action: str,
        pages: str | None,
        options: dict[str, object],
    ) -> None:
        try:
            summary = convert_files(
                files,
                output,
                action,
                page_ranges=pages,
                options=options,
                progress_callback=lambda done, total, message: self.event_queue.put(("progress", (done, total, message))),
                log_callback=lambda message: self.event_queue.put(("log", message)),
            )
            self.event_queue.put(("done", summary))
        except Exception as exc:
            self.event_queue.put(("error", exc))

    def _drain_queue(self) -> None:
        try:
            while True:
                event, payload = self.event_queue.get_nowait()
                if event == "progress":
                    done, total, message = payload  # type: ignore[misc]
                    self.progress.set(done / total if total else 0)
                    self.status.set(str(message))
                elif event == "log":
                    self._write_log(str(payload))
                elif event == "done":
                    self._finish_conversion(payload)
                elif event == "error":
                    self._fail_conversion(payload)
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def _finish_conversion(self, payload: object) -> None:
        self.is_converting = False
        self._record_activity()
        self.choose_button.configure(state="normal")
        self.output_button.configure(state="normal")
        summary = payload
        succeeded = getattr(summary, "succeeded", 0)
        failed = getattr(summary, "failed", 0)
        self.progress.set(1)
        if failed:
            self.status.set(f"Finished with {succeeded} success(es) and {failed} failure(s).")
            messagebox.showwarning(APP_NAME, self.status.get())
        else:
            self.status.set(f"Done. {succeeded} conversion(s) completed.")
            messagebox.showinfo(APP_NAME, self.status.get())
        if self.action.get() == "Compare PDF" and len(self.files) == 2:
            self._show_compare_window()
        self._validate()

    def _show_compare_window(self) -> None:
        window = ctk.CTkToplevel(self)
        window.title("PDF comparison")
        window.geometry("1000x650")
        window.grid_rowconfigure(1, weight=1)
        window.grid_columnconfigure(0, weight=1)
        window.grid_columnconfigure(1, weight=1)
        for column, path in enumerate(self.files[:2]):
            ctk.CTkLabel(window, text=path.name, font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=column, pady=10)
            box = ctk.CTkTextbox(window, wrap="word")
            box.grid(row=1, column=column, sticky="nsew", padx=8, pady=(0, 8))
            with fitz.open(path) as document:
                content = "\n\n".join(f"Page {index + 1}\n{page.get_text()}" for index, page in enumerate(document))
            box.insert("end", content)
            box.configure(state="disabled")

    def _fail_conversion(self, payload: object) -> None:
        self.is_converting = False
        self._record_activity()
        self.choose_button.configure(state="normal")
        self.output_button.configure(state="normal")
        self.status.set(str(payload))
        self._write_log(f"Could not start conversion: {payload}")
        messagebox.showerror(APP_NAME, str(payload))
        self._validate()

    def _write_log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")


def main() -> None:
    app = LocalPDFConverterApp()
    app.mainloop()
