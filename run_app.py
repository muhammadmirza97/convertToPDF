"""Launch Local PDF Toolbox.

The desktop shortcut starts this through pythonw.exe, so there is no console window to show
an error. Any startup failure is therefore written to logs/app.log and shown in a dialog.
"""

from __future__ import annotations

import sys
import traceback


def _report_startup_failure(error: BaseException) -> None:
    details = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    try:
        from src.logger import setup_logging

        setup_logging().error("Startup failed:\n%s", details)
    except Exception:
        pass  # Logging must never hide the original error.

    message = (
        f"{type(error).__name__}: {error}\n\n"
        "Local PDF Toolbox could not start.\n"
        "Details were written to logs\\app.log.\n\n"
        "If dependencies are missing, run this in the project folder:\n"
        "  .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
    )
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Local PDF Toolbox", message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def main() -> int:
    try:
        from src.app import main as start_app
    except Exception as error:
        _report_startup_failure(error)
        return 1

    try:
        start_app()
    except Exception as error:
        _report_startup_failure(error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
