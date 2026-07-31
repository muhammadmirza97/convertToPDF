"""CustomTkinter tool dashboard for Local PDF Toolbox."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .config import (
    APP_ICON_ICO,
    APP_ICON_PNG,
    APP_NAME,
    APP_VERSION,
    CATEGORIES,
    DEFAULT_OUTPUT_DIR,
    INACTIVITY_TIMEOUT_MINUTES,
    INACTIVITY_WARNING_SECONDS,
    REQUIRES_LIBREOFFICE,
    REQUIRES_TESSERACT,
    SUPPORTED_INPUT_EXTENSIONS,
)
from .converter import run_tool
from .file_validation import (
    DEPENDENCY_LABELS,
    detect_input_types,
    missing_dependencies,
    validate_tool,
)
from .gui_forms import FormWorkspace
from .gui_organize import OrganizeWorkspace
from .gui_signature import SignaturePad
from .logger import setup_logging
from .ocr_tools import available_languages, find_tesseract
from .office_tools import find_libreoffice
from .tool_registry import (
    KIND_BOOL,
    KIND_CHOICE,
    KIND_FILE,
    KIND_PASSWORD,
    KIND_SIGNATURE,
    Option,
    Tool,
    tools_in_category,
)

try:  # Drag-and-drop is optional; the app works without it.
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
except Exception:  # pragma: no cover - depends on the local install
    DND_FILES = None
    TkinterDnD = None
    DND_AVAILABLE = False


FILE_TYPE_FILTERS = [
    ("Supported files", "*.pdf *.png *.jpg *.jpeg *.txt *.html *.htm *.docx *.doc *.pptx *.ppt *.xlsx *.xls"),
    ("PDF files", "*.pdf"),
    ("Images", "*.png *.jpg *.jpeg"),
    ("Text files", "*.txt"),
    ("HTML files", "*.html *.htm"),
    ("Office files", "*.docx *.doc *.pptx *.ppt *.xlsx *.xls"),
    ("All files", "*.*"),
]


def open_in_file_manager(path: Path) -> None:
    """Open a folder in the system file manager."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # noqa: S606 - local user action
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError:
        pass


_DND_BASES = (ctk.CTk, TkinterDnD.DnDWrapper) if DND_AVAILABLE else (ctk.CTk,)


class LocalPDFToolboxApp(*_DND_BASES):  # type: ignore[misc]
    def __init__(self, *, inactivity_timeout_minutes: float = INACTIVITY_TIMEOUT_MINUTES) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1180x780")
        self.minsize(980, 680)
        self._apply_window_icon()

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.dnd_enabled = False
        if DND_AVAILABLE:
            try:
                # CustomTkinter has no TkinterDnD root, so the wrapper is initialised here.
                self.TkdndVersion = TkinterDnD._require(self)
                self.dnd_enabled = True
            except Exception:
                self.dnd_enabled = False

        self.logger = setup_logging()
        self.libreoffice_path = find_libreoffice()
        self.tesseract_path = find_tesseract()
        self.missing_dependencies: set[str] = missing_dependencies()

        self.files: list[Path] = []
        self.tool: Tool | None = None
        self.option_vars: dict[str, tk.Variable] = {}
        self.tool_buttons: dict[str, ctk.CTkButton] = {}

        self.output_folder = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.status = tk.StringVar(value="Choose a tool on the left, then add files.")
        self.input_type = tk.StringVar(value="No files selected")
        self.tool_title = tk.StringVar(value="No tool selected")
        self.tool_description = tk.StringVar(value="")

        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.is_running = False
        self.last_output_folder: Path | None = None

        self.inactivity_timeout_seconds = max(0.0, float(inactivity_timeout_minutes) * 60)
        self.last_activity = time.monotonic()
        self.idle_warning: ctk.CTkToplevel | None = None
        self.closed_for_inactivity = False

        self.logger.info(
            "App startup. LibreOffice: %s | Tesseract: %s | drag-and-drop: %s",
            self.libreoffice_path or "not detected",
            self.tesseract_path or "not detected",
            "on" if self.dnd_enabled else "off",
        )
        self._build_ui()
        self._select_first_tool()
        self._start_activity_tracking()
        self.after(100, self._drain_queue)

    # --- window chrome ----------------------------------------------------

    def _apply_window_icon(self) -> None:
        """Use the app icon for the window and taskbar, if the asset is present."""
        try:
            if sys.platform.startswith("win") and APP_ICON_ICO.is_file():
                self.iconbitmap(default=str(APP_ICON_ICO))
            elif APP_ICON_PNG.is_file():
                self._icon_image = tk.PhotoImage(file=str(APP_ICON_PNG))
                self.iconphoto(True, self._icon_image)
        except tk.TclError:
            pass  # An unusable icon must never stop the app from opening.

    # --- inactivity timeout ------------------------------------------------

    def _start_activity_tracking(self) -> None:
        """Watch for any input, and close the app after a long idle period."""
        if not self.inactivity_timeout_seconds:
            return
        for sequence in ("<Any-KeyPress>", "<Any-Button>", "<Motion>", "<MouseWheel>"):
            # bind_all covers the workspace and signature windows too.
            self.bind_all(sequence, self._mark_activity, add="+")
        self.after(1000, self._check_inactivity)

    def _mark_activity(self, _event=None) -> None:
        self.last_activity = time.monotonic()
        if self.idle_warning is not None:
            self._dismiss_idle_warning()

    def seconds_idle(self) -> float:
        return max(0.0, time.monotonic() - self.last_activity)

    def seconds_until_close(self) -> float:
        return max(0.0, self.inactivity_timeout_seconds - self.seconds_idle())

    def _check_inactivity(self) -> None:
        if not self.inactivity_timeout_seconds:
            return

        # A running job counts as activity, so a long OCR run is never cut short.
        if self.is_running:
            self.last_activity = time.monotonic()

        remaining = self.seconds_until_close()
        if remaining <= 0:
            self._close_for_inactivity()
            return
        if remaining <= INACTIVITY_WARNING_SECONDS:
            self._show_idle_warning(remaining)

        self.after(1000, self._check_inactivity)

    def _idle_label(self) -> str:
        """Describe the timeout the way a person would say it."""
        seconds = self.inactivity_timeout_seconds
        if seconds >= 60:
            minutes = seconds / 60
            shown = int(minutes) if float(minutes).is_integer() else round(minutes, 1)
            return f"{shown} minute(s)"
        return f"{int(seconds)} second(s)"

    def _show_idle_warning(self, remaining: float) -> None:
        countdown = f"Closing in {int(remaining)} second(s) with no activity."
        if self.idle_warning is None:
            self.idle_warning = self._build_idle_warning()
        if self.idle_warning is not None:
            self.idle_countdown.set(countdown)

    def _build_idle_warning(self) -> ctk.CTkToplevel | None:
        try:
            window = ctk.CTkToplevel(self)
        except tk.TclError:
            return None
        window.title(f"{APP_NAME} - still there?")
        window.geometry("380x160")
        window.resizable(False, False)
        window.transient(self)
        window.protocol("WM_DELETE_WINDOW", self._mark_activity)

        self.idle_countdown = tk.StringVar(value="")
        ctk.CTkLabel(
            window,
            text=f"No activity for {self._idle_label()}.",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(padx=20, pady=(22, 6))
        ctk.CTkLabel(window, textvariable=self.idle_countdown).pack(padx=20)
        ctk.CTkButton(window, text="Keep working", width=140, command=self._mark_activity).pack(
            pady=18
        )
        try:
            window.attributes("-topmost", True)
        except tk.TclError:
            pass
        return window

    def _dismiss_idle_warning(self) -> None:
        window, self.idle_warning = self.idle_warning, None
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass

    def _close_for_inactivity(self) -> None:
        self.logger.info("Closing after %s of inactivity.", self._idle_label())
        self.closed_for_inactivity = True
        self._dismiss_idle_warning()
        # quit() ends the event loop, which returns from mainloop() and lets the process
        # exit. destroy() is best effort: CustomTkinter's own teardown can raise if one of
        # its timers is still queued, and that must not stop the app from closing.
        try:
            self.quit()
        except tk.TclError:
            pass
        try:
            self.destroy()
        except tk.TclError:
            pass

    def _dependency_summary(self) -> str:
        """One line per optional local engine, shown in the header."""
        lines = []
        for key, path in (
            (REQUIRES_LIBREOFFICE, self.libreoffice_path),
            (REQUIRES_TESSERACT, self.tesseract_path),
        ):
            label = DEPENDENCY_LABELS[key]
            if key in self.missing_dependencies:
                lines.append(f"{label}: not detected")
            elif key == REQUIRES_TESSERACT:
                languages = ", ".join(available_languages()) or "no language packs"
                lines.append(f"{label}: ready ({languages})")
            else:
                lines.append(f"{label}: ready")
        if not self.dnd_enabled:
            lines.append("Drag and drop: unavailable")
        return "\n".join(lines)

    # --- layout -----------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=APP_NAME, font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=22, pady=(14, 0)
        )
        ctk.CTkLabel(
            header,
            text="Everything runs on this computer. Nothing is uploaded.",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 12))
        ctk.CTkLabel(
            header, text=self._dependency_summary(), text_color=("gray35", "gray75"), justify="right"
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=22)

        self.sidebar = ctk.CTkScrollableFrame(self, width=250, label_text="Tools")
        self.sidebar.grid(row=1, column=0, sticky="nsw", padx=(16, 8), pady=12)
        self._build_sidebar()

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=12)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(3, weight=1)

        title_box = ctk.CTkFrame(body, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        title_box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            title_box, textvariable=self.tool_title, font=ctk.CTkFont(size=18, weight="bold"), anchor="w"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_box, textvariable=self.tool_description, text_color=("gray35", "gray75"), anchor="w", justify="left"
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        files_box = ctk.CTkFrame(body)
        files_box.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        files_box.grid_columnconfigure(3, weight=1)
        ctk.CTkButton(files_box, text="Add files", width=110, command=self._choose_files).grid(
            row=0, column=0, padx=(12, 8), pady=12
        )
        ctk.CTkButton(files_box, text="Clear", width=80, command=self._clear_files).grid(
            row=0, column=1, padx=(0, 8), pady=12
        )
        ctk.CTkButton(files_box, text="Output folder", width=120, command=self._choose_output).grid(
            row=0, column=2, padx=(0, 8), pady=12
        )
        self.output_entry = ctk.CTkEntry(files_box, textvariable=self.output_folder)
        self.output_entry.grid(row=0, column=3, padx=(0, 12), pady=12, sticky="ew")
        self.output_entry.bind("<KeyRelease>", lambda _event: self._validate())

        drop_hint = (
            "Drop files here, or press Add files"
            if self.dnd_enabled
            else "No files selected"
        )
        self.files_label = ctk.CTkLabel(files_box, text=drop_hint, anchor="w", justify="left")
        self.files_label.grid(row=1, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 10))
        self._register_drop_target(files_box)
        self._register_drop_target(self.files_label)

        options_box = ctk.CTkFrame(body, fg_color="transparent")
        options_box.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        options_box.grid_columnconfigure(0, weight=1)
        self.options_frame = ctk.CTkScrollableFrame(options_box, label_text="Options", height=210)
        self.options_frame.grid(row=0, column=0, sticky="ew")
        self.options_frame.grid_columnconfigure(1, weight=1)
        self.workspace_button = ctk.CTkButton(
            options_box, text="Open workspace", width=150, command=self._open_workspace
        )
        self.workspace_button.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.workspace_button.grid_remove()

        self.log_box = ctk.CTkTextbox(body, wrap="word", height=140)
        self.log_box.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 8))
        self.log_box.insert("end", "Results will appear here.\n")
        self.log_box.configure(state="disabled")

        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, textvariable=self.status, anchor="w").grid(row=0, column=0, sticky="ew")
        self.progress = ctk.CTkProgressBar(footer)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.progress.set(0)
        self.open_button = ctk.CTkButton(
            footer, text="Open output folder", width=150, command=self._open_output, state="disabled"
        )
        self.open_button.grid(row=0, column=1, rowspan=2, padx=(12, 8))
        self.run_button = ctk.CTkButton(footer, text="Run tool", width=130, command=self._start_run)
        self.run_button.grid(row=0, column=2, rowspan=2)

    def _build_sidebar(self) -> None:
        row = 0
        for category in CATEGORIES:
            tools = tools_in_category(category)
            if not tools:
                continue
            ctk.CTkLabel(
                self.sidebar,
                text=category.upper(),
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("gray40", "gray70"),
                anchor="w",
            ).grid(row=row, column=0, sticky="ew", padx=6, pady=(12, 2))
            row += 1
            for tool in tools:
                unavailable = tool.requires is not None and tool.requires in self.missing_dependencies
                if unavailable:
                    needed = DEPENDENCY_LABELS.get(tool.requires, tool.requires)
                    label = f"{tool.label}  (needs {needed})"
                else:
                    label = tool.label
                button = ctk.CTkButton(
                    self.sidebar,
                    text=label,
                    anchor="w",
                    height=30,
                    fg_color="transparent",
                    text_color=("gray20", "gray90"),
                    hover_color=("gray85", "gray25"),
                    state="disabled" if unavailable else "normal",
                    command=lambda selected=tool: self._select_tool(selected),
                )
                button.grid(row=row, column=0, sticky="ew", padx=4, pady=1)
                self.tool_buttons[tool.id] = button
                row += 1

    # --- tool selection ---------------------------------------------------

    def _select_first_tool(self) -> None:
        for category in CATEGORIES:
            for tool in tools_in_category(category):
                if tool.requires is None or tool.requires not in self.missing_dependencies:
                    self._select_tool(tool)
                    return

    def _select_tool(self, tool: Tool) -> None:
        self.tool = tool
        self.tool_title.set(tool.label)
        description = tool.description
        if tool.hint:
            description = f"{description}\n{tool.hint}"
        self.tool_description.set(description)

        for tool_id, button in self.tool_buttons.items():
            selected = tool_id == tool.id
            button.configure(fg_color=("gray80", "gray30") if selected else "transparent")

        self._build_options(tool)
        if tool.workspace:
            self.workspace_button.grid()
        else:
            self.workspace_button.grid_remove()
        self._validate()

    # --- interactive helpers ---------------------------------------------

    def _open_workspace(self) -> None:
        """Open the interactive helper the selected tool offers."""
        tool = self.tool
        if tool is None or not tool.workspace:
            return
        if not self.files:
            messagebox.showinfo(APP_NAME, "Add a PDF first, then open the workspace.")
            return
        if len(self.files) > 1:
            self._write_log(f"Workspace uses the first file: {self.files[0].name}")

        password_var = self.option_vars.get("password")
        password = password_var.get() if password_var else ""
        try:
            if tool.workspace == "organize":
                OrganizeWorkspace(
                    self,
                    self.files[0],
                    password=password,
                    on_apply=lambda plan: self._apply_workspace_value("plan", plan, "Page plan"),
                )
            elif tool.workspace == "form":
                FormWorkspace(
                    self,
                    self.files[0],
                    password=password,
                    on_apply=lambda values: self._apply_workspace_value(
                        "field_values", values, "Field values"
                    ),
                )
            else:
                messagebox.showinfo(APP_NAME, f"No workspace named {tool.workspace}.")
        except ValueError as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def _apply_workspace_value(self, option_key: str, value: str, label: str) -> None:
        """Write a value produced by a workspace back into the tool's option form."""
        variable = self.option_vars.get(option_key)
        if variable is not None:
            variable.set(value)
        self._write_log(f"{label} set to: {value}")
        self._validate()

    def _apply_page_plan(self, plan: str) -> None:
        """Kept for callers and tests that set a page plan directly."""
        self._apply_workspace_value("plan", plan, "Page plan")

    def _draw_signature(self, variable: tk.Variable) -> None:
        SignaturePad(self, on_save=lambda path: self._signature_saved(variable, path))

    def _signature_saved(self, variable: tk.Variable, path: Path) -> None:
        variable.set(str(path))
        self._write_log(f"Signature saved to {path}")

    def _build_options(self, tool: Tool) -> None:
        for child in self.options_frame.winfo_children():
            child.destroy()
        self.option_vars.clear()

        if not tool.options:
            ctk.CTkLabel(
                self.options_frame, text="This tool has no options.", text_color=("gray40", "gray70")
            ).grid(row=0, column=0, sticky="w", padx=8, pady=8)
            return

        for row, option in enumerate(tool.options):
            self._build_option_row(row, option)

    def _build_option_row(self, row: int, option: Option) -> None:
        if option.kind == KIND_BOOL:
            variable = tk.BooleanVar(value=bool(option.default))
            widget = ctk.CTkSwitch(self.options_frame, text=option.label, variable=variable)
            widget.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=6)
            self.option_vars[option.key] = variable
            if option.help:
                ctk.CTkLabel(
                    self.options_frame, text=option.help, text_color=("gray45", "gray65"), anchor="w"
                ).grid(row=row, column=2, sticky="w", padx=8)
            return

        ctk.CTkLabel(self.options_frame, text=option.label, anchor="w").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        variable = tk.StringVar(value="" if option.default is None else str(option.default))
        self.option_vars[option.key] = variable

        if option.kind == KIND_CHOICE:
            widget = ctk.CTkOptionMenu(self.options_frame, values=list(option.choices), variable=variable)
            widget.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        elif option.kind in (KIND_FILE, KIND_SIGNATURE):
            holder = ctk.CTkFrame(self.options_frame, fg_color="transparent")
            holder.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
            holder.grid_columnconfigure(0, weight=1)
            entry = ctk.CTkEntry(holder, textvariable=variable, placeholder_text=option.placeholder)
            entry.grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                holder, text="Browse", width=80, command=lambda var=variable: self._choose_option_file(var)
            ).grid(row=0, column=1, padx=(8, 0))
            if option.kind == KIND_SIGNATURE:
                ctk.CTkButton(
                    holder, text="Draw", width=70, command=lambda var=variable: self._draw_signature(var)
                ).grid(row=0, column=2, padx=(8, 0))
        else:
            entry = ctk.CTkEntry(
                self.options_frame,
                textvariable=variable,
                placeholder_text=option.placeholder,
                show="*" if option.kind == KIND_PASSWORD else "",
            )
            entry.grid(row=row, column=1, sticky="ew", padx=8, pady=6)

        if option.help:
            ctk.CTkLabel(
                self.options_frame, text=option.help, text_color=("gray45", "gray65"), anchor="w"
            ).grid(row=row, column=2, sticky="w", padx=8)

    def _choose_option_file(self, variable: tk.Variable) -> None:
        selected = filedialog.askopenfilename(title="Choose a file", filetypes=FILE_TYPE_FILTERS)
        if selected:
            variable.set(selected)

    # --- files ------------------------------------------------------------

    def _choose_files(self) -> None:
        selected = filedialog.askopenfilenames(title="Select files", filetypes=FILE_TYPE_FILTERS)
        if not selected:
            return
        for item in selected:
            path = Path(item)
            if path not in self.files:
                self.files.append(path)
        self._write_log(f"Added {len(selected)} file(s).")
        self._refresh_file_label()
        self._validate()

    def _register_drop_target(self, widget) -> None:
        if not self.dnd_enabled:
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event) -> None:
        """Add dropped files, ignoring anything the app cannot read."""
        try:
            dropped = self.tk.splitlist(event.data)
        except Exception:
            dropped = [event.data]

        added, rejected = 0, 0
        for item in dropped:
            path = Path(str(item).strip("{}"))
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
                rejected += 1
                continue
            if path not in self.files:
                self.files.append(path)
                added += 1

        message = f"Added {added} dropped file(s)."
        if rejected:
            message += f" Ignored {rejected} unsupported file(s)."
        self._write_log(message)
        self._refresh_file_label()
        self._validate()

    def _clear_files(self) -> None:
        self.files = []
        self._refresh_file_label()
        self._validate()

    def _refresh_file_label(self) -> None:
        if not self.files:
            empty = "Drop files here, or press Add files" if self.dnd_enabled else "No files selected"
            self.files_label.configure(text=empty)
            self.input_type.set("No files selected")
            return
        names = [path.name for path in self.files]
        shown = ", ".join(names[:6])
        if len(names) > 6:
            shown = f"{shown} and {len(names) - 6} more"
        types = ", ".join(sorted(detect_input_types(self.files)))
        self.files_label.configure(text=f"{len(names)} file(s) [{types}]: {shown}")

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(title="Choose output folder", initialdir=self.output_folder.get())
        if selected:
            self.output_folder.set(selected)
            self._write_log(f"Output folder: {selected}")
            self._validate()

    def _open_output(self) -> None:
        target = self.last_output_folder or Path(self.output_folder.get())
        if target.is_dir():
            open_in_file_manager(target)

    # --- running ----------------------------------------------------------

    def _collect_options(self) -> dict[str, object]:
        return {key: variable.get() for key, variable in self.option_vars.items()}

    def _validate(self) -> None:
        if self.is_running:
            self.run_button.configure(state="disabled")
            return

        result = validate_tool(
            self.tool,
            self.files,
            self.output_folder.get(),
            missing_dependencies=self.missing_dependencies,
        )
        self.status.set(result.message)
        self.run_button.configure(state="normal" if result.ok else "disabled")

    def _start_run(self) -> None:
        if self.tool is None:
            return
        self.is_running = True
        self.run_button.configure(state="disabled")
        self.progress.set(0)
        self.status.set(f"Running {self.tool.label}...")
        self._write_log(f"--- {self.tool.label} on {len(self.files)} file(s) ---")

        tool = self.tool
        files = list(self.files)
        output_dir = self.output_folder.get()
        options = self._collect_options()
        thread = threading.Thread(
            target=self._run_worker, args=(tool, files, output_dir, options), daemon=True
        )
        thread.start()

    def _run_worker(self, tool: Tool, files: list[Path], output_dir: str, options: dict) -> None:
        try:
            summary = run_tool(
                tool,
                files,
                output_dir,
                options,
                progress_callback=lambda done, total, message: self.event_queue.put(
                    ("progress", (done, total, message))
                ),
                log_callback=lambda message: self.event_queue.put(("log", message)),
            )
            self.event_queue.put(("done", (summary, output_dir)))
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
                    self._finish_run(*payload)  # type: ignore[misc]
                elif event == "error":
                    self._fail_run(payload)
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def _finish_run(self, summary, output_dir: str) -> None:
        self.is_running = False
        self.progress.set(1)
        self.last_output_folder = Path(output_dir)
        self.open_button.configure(state="normal")
        if summary.failed:
            self.status.set(f"Finished with {summary.succeeded} success(es) and {summary.failed} failure(s).")
            messagebox.showwarning(APP_NAME, self.status.get())
        else:
            self.status.set(f"Done. {summary.succeeded} task(s) completed.")
            messagebox.showinfo(APP_NAME, f"{self.status.get()}\nSaved in: {output_dir}")
        self._validate()

    def _fail_run(self, payload: object) -> None:
        self.is_running = False
        self.status.set(str(payload))
        self._write_log(f"Could not start: {payload}")
        messagebox.showerror(APP_NAME, str(payload))
        self._validate()

    def _write_log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")


# Kept so older imports keep working.
LocalPDFConverterApp = LocalPDFToolboxApp


def main() -> None:
    app = LocalPDFToolboxApp()
    app.mainloop()
    # The loop also ends when the app closes itself after a long idle period.
    try:
        app.destroy()
    except tk.TclError:
        pass
