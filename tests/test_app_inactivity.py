from __future__ import annotations

from src.app import LocalPDFConverterApp
from src.config import (
    DEFAULT_INACTIVITY_TIMEOUT_SECONDS,
    INACTIVITY_TIMEOUT_ENV,
    get_inactivity_timeout_ms,
)


class _FakeLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str, *args: object) -> None:
        self.messages.append(message % args if args else message)


class _FakeApp:
    def __init__(self, *, converting: bool = False) -> None:
        self._inactivity_after_id: str | None = "old-timer"
        self.inactivity_timeout_ms = get_inactivity_timeout_ms()
        self.is_converting = converting
        self.logger = _FakeLogger()
        self.cancelled: list[str] = []
        self.scheduled: list[tuple[int, object]] = []
        self.destroyed = False

    def after_cancel(self, timer_id: str) -> None:
        self.cancelled.append(timer_id)

    def after(self, delay: int, callback: object) -> str:
        self.scheduled.append((delay, callback))
        return "new-timer"

    def destroy(self) -> None:
        self.destroyed = True

    _record_activity = LocalPDFConverterApp._record_activity
    _close_for_inactivity = LocalPDFConverterApp._close_for_inactivity


def test_default_timeout_is_thirty_minutes(monkeypatch):
    monkeypatch.delenv(INACTIVITY_TIMEOUT_ENV, raising=False)

    assert DEFAULT_INACTIVITY_TIMEOUT_SECONDS == 1800
    assert get_inactivity_timeout_ms() == 1_800_000


def test_timeout_can_be_overridden_for_testing(monkeypatch):
    monkeypatch.setenv(INACTIVITY_TIMEOUT_ENV, "60")

    assert get_inactivity_timeout_ms() == 60_000


def test_invalid_timeout_override_uses_default(monkeypatch):
    monkeypatch.setenv(INACTIVITY_TIMEOUT_ENV, "not-a-number")

    assert get_inactivity_timeout_ms() == 1_800_000


def test_activity_resets_thirty_minute_timer(monkeypatch):
    monkeypatch.delenv(INACTIVITY_TIMEOUT_ENV, raising=False)
    app = _FakeApp()

    app._record_activity()

    assert app.cancelled == ["old-timer"]
    assert app.scheduled == [(1_800_000, app._close_for_inactivity)]
    assert app._inactivity_after_id == "new-timer"


def test_idle_app_closes_automatically(monkeypatch):
    monkeypatch.delenv(INACTIVITY_TIMEOUT_ENV, raising=False)
    app = _FakeApp()

    app._close_for_inactivity()

    assert app.destroyed
    assert app.logger.messages == ["App closed automatically after 1800 seconds of inactivity."]


def test_idle_log_reports_timeout_override(monkeypatch):
    monkeypatch.setenv(INACTIVITY_TIMEOUT_ENV, "60")
    app = _FakeApp()

    app._close_for_inactivity()

    assert app.logger.messages == ["App closed automatically after 60 seconds of inactivity."]


def test_active_conversion_is_not_interrupted(monkeypatch):
    monkeypatch.delenv(INACTIVITY_TIMEOUT_ENV, raising=False)
    app = _FakeApp(converting=True)

    app._close_for_inactivity()

    assert not app.destroyed
    assert app.scheduled == [(1_800_000, app._close_for_inactivity)]
