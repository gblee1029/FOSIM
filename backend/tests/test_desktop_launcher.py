from __future__ import annotations

import desktop_launcher


class _FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_wait_for_http_ok_retries_until_endpoint_returns_success(monkeypatch) -> None:
    outcomes: list[object] = [OSError("not listening yet"), _FakeResponse(200)]
    attempts: list[tuple[str, float]] = []
    sleeps: list[float] = []

    def fake_urlopen(url: str, timeout: float) -> object:
        attempts.append((url, timeout))
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(desktop_launcher.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(desktop_launcher.time, "sleep", sleeps.append)

    assert desktop_launcher._wait_for_http_ok(
        "http://127.0.0.1:8000/api/health",
        timeout_seconds=2.0,
        interval_seconds=0.1,
    )
    assert attempts == [
        ("http://127.0.0.1:8000/api/health", 1.0),
        ("http://127.0.0.1:8000/api/health", 1.0),
    ]
    assert sleeps == [0.1]


def test_open_browser_waits_for_health_endpoint_before_launch(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    def fake_wait(url: str, *args: object, **kwargs: object) -> bool:
        events.append(("wait", url))
        return True

    def fake_open(url: str) -> bool:
        events.append(("open", url))
        return True

    monkeypatch.setattr(desktop_launcher, "_wait_for_http_ok", fake_wait)
    monkeypatch.setattr(desktop_launcher, "_browser_launch_url", lambda url: f"{url}?startup=123")
    monkeypatch.setattr(desktop_launcher.webbrowser, "open_new_tab", fake_open)

    desktop_launcher._open_browser("http://127.0.0.1:8000")

    assert events == [
        ("wait", "http://127.0.0.1:8000/api/health"),
        ("open", "http://127.0.0.1:8000?startup=123"),
    ]


def test_open_browser_does_not_launch_when_server_never_becomes_ready(monkeypatch) -> None:
    opened_urls: list[str] = []

    monkeypatch.setattr(desktop_launcher, "_wait_for_http_ok", lambda *args, **kwargs: False)
    monkeypatch.setattr(desktop_launcher.webbrowser, "open_new_tab", opened_urls.append)

    desktop_launcher._open_browser("http://127.0.0.1:8000")

    assert opened_urls == []


def test_browser_launch_url_adds_unique_query_parameter(monkeypatch) -> None:
    monkeypatch.setattr(desktop_launcher.time, "time", lambda: 1234.567)

    assert (
        desktop_launcher._browser_launch_url("http://127.0.0.1:8000/")
        == "http://127.0.0.1:8000/?startup=1234567"
    )
