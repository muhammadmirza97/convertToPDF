"""CustomTkinter desktop GUI for Local PDF Converter."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .config import (
    ACTION_AUTO,
    ACTION_SPLIT_PDF,
    ACTION_OFFICE_TO_PDF,
    ACTIONS,
    APP_NAME,
    DEFAULT_OUTPUT_DIR,
)
from .converter import convert_files
from .file_validation import detect_input_types, validate_action
from .logger import setup_logging
from .office_tools import find_libreoffice


class LocalPDFConverterApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("980x700")
        self.minsize(820, 600)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.logger = setup_logging()
        self.files: list[Path] = []
        self.output_folder = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.action = tk.StringVar(value=ACTION_AUTO)
        self.page_ranges = tk.StringVar(value="")
        self.status = tk.StringVar(value="Choose files, an output folder, and an action.")
        self.input_type = tk.StringVar(value="No files selected")
        self.libreoffice_path = find_libreoffice()
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.is_converting = False
        self.logger.info("App startup. LibreOffice detected: %s", self.libreoffice_path or "not detected")

        self._build_ui()
        self._validate()
        self.after(100, self._drain_queue)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        title = ctk.CTkLabel(header, text=APP_NAME, font=ctk.CTkFont(size=26, weight="bold"))
        title.grid(row=0, column=0, sticky="w", padx=24, pady=(18, 2))
        subtitle_text = "Local-only desktop conversion. Files stay on this computer."
        subtitle = ctk.CTkLabel(header, text=subtitle_text, text_color=("gray35", "gray75"))
        subtitle.grid(row=1, column=0, sticky="w", padx=24, pady=(0, 16))

        controls = ctk.CTkFrame(self, corner_radius=0)
        controls.grid(row=1, column=0, sticky="ew", padx=20, pady=16)
        controls.grid_columnconfigure(1, weight=1)
        controls.grid_columnconfigure(3, weight=1)

        self.choose_button = ctk.CTkButton(controls, text="Select files", command=self._choose_files)
        self.choose_button.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="ew")
        self.file_count_label = ctk.CTkLabel(controls, text="0 files", anchor="w")
        self.file_count_label.grid(row=0, column=1, padx=(0, 16), pady=10, sticky="ew")

        self.output_button = ctk.CTkButton(controls, text="Output folder", command=self._choose_output)
        self.output_button.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="ew")
        self.output_entry = ctk.CTkEntry(controls, textvariable=self.output_folder)
        self.output_entry.grid(row=0, column=3, pady=10, sticky="ew")
        self.output_entry.bind("<KeyRelease>", lambda _event: self._validate())

        action_label = ctk.CTkLabel(controls, text="Action", anchor="w")
        action_label.grid(row=1, column=0, padx=(0, 10), pady=(2, 10), sticky="w")
        action_values = ACTIONS if self.libreoffice_path else [item for item in ACTIONS if item != ACTION_OFFICE_TO_PDF]
        self.action_menu = ctk.CTkOptionMenu(controls, values=action_values, variable=self.action, command=lambda _value: self._validate())
        self.action_menu.grid(row=1, column=1, padx=(0, 16), pady=(2, 10), sticky="ew")

        ranges_label = ctk.CTkLabel(controls, text="Pages", anchor="w")
        ranges_label.grid(row=1, column=2, padx=(0, 10), pady=(2, 10), sticky="w")
        self.ranges_entry = ctk.CTkEntry(controls, textvariable=self.page_ranges, placeholder_text="1-3,5 or blank")
        self.ranges_entry.grid(row=1, column=3, pady=(2, 10), sticky="ew")
        self.ranges_entry.bind("<KeyRelease>", lambda _event: self._validate())

        info = ctk.CTkFrame(self, corner_radius=0)
        info.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 16))
        info.grid_columnconfigure(0, weight=1)
        info.grid_rowconfigure(1, weight=1)

        top_line = ctk.CTkFrame(info, fg_color="transparent")
        top_line.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        top_line.grid_columnconfigure(1, weight=1)
        self.type_label = ctk.CTkLabel(top_line, textvariable=self.input_type, anchor="w")
        self.type_label.grid(row=0, column=0, sticky="w")
        libre_text = f"LibreOffice: {self.libreoffice_path}" if self.libreoffice_path else "LibreOffice: not detected; Office to PDF is hidden"
        self.libre_label = ctk.CTkLabel(top_line, text=libre_text, text_color=("gray35", "gray75"), anchor="e")
        self.libre_label.grid(row=0, column=1, sticky="e")

        self.log_box = ctk.CTkTextbox(info, wrap="word")
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.log_box.insert("end", "Conversion log will appear here.\n")
        self.log_box.configure(state="disabled")

        footer = ctk.CTkFrame(self, corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        footer.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(footer, textvariable=self.status, anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=(12, 4))
        self.progress = ctk.CTkProgressBar(footer)
        self.progress.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))
        self.progress.set(0)
        self.convert_button = ctk.CTkButton(footer, text="Convert", command=self._start_conversion)
        self.convert_button.grid(row=0, column=1, rowspan=2, sticky="nsew", pady=12)

    def _choose_files(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Select files",
            filetypes=[
                ("Supported files", "*.pdf *.png *.jpg *.jpeg *.txt *.docx *.doc *.pptx *.ppt *.xlsx *.xls"),
                ("PDF files", "*.pdf"),
                ("Images", "*.png *.jpg *.jpeg"),
                ("Text files", "*.txt"),
                ("Office files", "*.docx *.doc *.pptx *.ppt *.xlsx *.xls"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.files = [Path(path) for path in selected]
            self.file_count_label.configure(text=f"{len(self.files)} file(s) selected")
            self._write_log(f"Selected {len(self.files)} file(s).")
            self._validate()

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
        if action == ACTION_SPLIT_PDF:
            self.ranges_entry.configure(state="normal")
        else:
            self.ranges_entry.configure(state="disabled")

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
        files = list(self.files)
        output = self.output_folder.get()
        action = self.action.get()
        pages = self.page_ranges.get().strip() or None
        self.is_converting = True
        self.convert_button.configure(state="disabled")
        self.choose_button.configure(state="disabled")
        self.output_button.configure(state="disabled")
        self.progress.set(0)
        self.status.set("Starting conversion...")
        self._write_log(f"Starting conversion: {action}.")

        thread = threading.Thread(
            target=self._run_conversion,
            args=(files, output, action, pages),
            daemon=True,
        )
        thread.start()

    def _run_conversion(
        self,
        files: list[Path],
        output: str,
        action: str,
        pages: str | None,
    ) -> None:
        try:
            summary = convert_files(
                files,
                output,
                action,
                page_ranges=pages,
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
        self._validate()

    def _fail_conversion(self, payload: object) -> None:
        self.is_converting = False
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
