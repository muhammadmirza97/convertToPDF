"""Window icon and inactivity-timeout behaviour. Skipped when Tk cannot start."""

from __future__ import annotations

import time
import tkinter as tk

import pytest

from src.config import (
    APP_ICON_ICO,
    APP_ICON_PNG,
    DEFAULT_INACTIVITY_TIMEOUT_MINUTES,
    INACTIVITY_TIMEOUT_MINUTES,
    idle_timeout_minutes,
)


def _new_app(**kwargs):
    from src.app import LocalPDFToolboxApp

    try:
        return LocalPDFToolboxApp(**kwargs)
    except tk.TclError as exc:
        pytest.skip(f"Tk is not usable here: {exc}")


def _idle_for(app, seconds: float) -> None:
    """Pretend the last activity happened `seconds` ago."""
    app.last_activity = time.monotonic() - seconds


def _still_open(app) -> bool:
    """A destroyed root window may report 0 or raise; both mean closed."""
    try:
        return bool(app.winfo_exists())
    except tk.TclError:
        return False


def test_icon_assets_exist():
    assert APP_ICON_ICO.is_file()
    assert APP_ICON_PNG.is_file()


def test_default_timeout_is_thirty_minutes():
    assert DEFAULT_INACTIVITY_TIMEOUT_MINUTES == 30
    assert idle_timeout_minutes(raw=None) == 30


def test_timeout_can_be_changed_by_environment_variable():
    assert idle_timeout_minutes(raw="5") == 5
    assert idle_timeout_minutes(raw="0") == 0        # 0 disables the timeout


def test_unreadable_timeout_falls_back_to_the_default():
    for bad in ("", "   ", "soon", "-10"):
        assert idle_timeout_minutes(raw=bad) == 30


def test_app_uses_the_configured_timeout():
    app = _new_app()
    try:
        assert app.inactivity_timeout_seconds == INACTIVITY_TIMEOUT_MINUTES * 60
        assert app.seconds_until_close() > INACTIVITY_TIMEOUT_MINUTES * 60 - 10
    finally:
        app.destroy()


def test_activity_resets_the_idle_clock():
    app = _new_app(inactivity_timeout_minutes=30)
    try:
        _idle_for(app, 600)
        assert app.seconds_idle() >= 600

        app._mark_activity()

        assert app.seconds_idle() < 1
    finally:
        app.destroy()


def test_idle_label_reads_naturally():
    app = _new_app(inactivity_timeout_minutes=30)
    try:
        assert app._idle_label() == "30 minute(s)"
        app.inactivity_timeout_seconds = 45
        assert app._idle_label() == "45 second(s)"
        app.inactivity_timeout_seconds = 90
        assert app._idle_label() == "1.5 minute(s)"
    finally:
        app.destroy()


def test_warning_appears_shortly_before_closing():
    app = _new_app(inactivity_timeout_minutes=1)
    try:
        _idle_for(app, 40)          # 20 seconds left of a 60 second timeout
        app._check_inactivity()
        app.update_idletasks()

        assert app.idle_warning is not None
        assert "Closing in" in app.idle_countdown.get()
        assert not app.closed_for_inactivity
    finally:
        app.destroy()


def test_activity_dismisses_the_warning():
    app = _new_app(inactivity_timeout_minutes=1)
    try:
        _idle_for(app, 40)
        app._check_inactivity()
        app.update_idletasks()
        assert app.idle_warning is not None

        app._mark_activity()

        assert app.idle_warning is None
        assert not app.closed_for_inactivity
    finally:
        app.destroy()


def test_app_shuts_itself_down_after_the_timeout():
    """The real check: the event loop ends by itself, so the process can exit."""
    app = _new_app(inactivity_timeout_minutes=1)
    try:
        _idle_for(app, 61)
        app.after(50, app._check_inactivity)
        app.after(8000, app.quit)  # safety net, so a failure cannot hang the suite

        app.mainloop()

        assert app.closed_for_inactivity
    finally:
        try:
            app.destroy()
        except tk.TclError:
            pass


def test_the_app_is_still_open_before_the_timeout():
    app = _new_app(inactivity_timeout_minutes=30)
    try:
        _idle_for(app, 120)

        app._check_inactivity()

        assert not app.closed_for_inactivity
        assert app.idle_warning is None
        assert _still_open(app)
    finally:
        app.destroy()


def test_a_running_job_is_never_interrupted():
    app = _new_app(inactivity_timeout_minutes=1)
    try:
        app.is_running = True
        _idle_for(app, 600)

        app._check_inactivity()

        assert not app.closed_for_inactivity
        assert app.seconds_idle() < 1  # the running job counted as activity
    finally:
        app.is_running = False
        app.destroy()


def test_zero_timeout_disables_the_feature():
    app = _new_app(inactivity_timeout_minutes=0)
    try:
        _idle_for(app, 100_000)

        app._check_inactivity()

        assert not app.closed_for_inactivity
        assert _still_open(app)
    finally:
        app.destroy()


def test_closing_the_warning_window_counts_as_activity():
    app = _new_app(inactivity_timeout_minutes=1)
    try:
        _idle_for(app, 40)
        app._check_inactivity()
        app.update_idletasks()

        # The warning's close button is wired to the same handler as any other input.
        app.idle_warning.protocol("WM_DELETE_WINDOW")
        app._mark_activity()

        assert app.idle_warning is None
    finally:
        app.destroy()
