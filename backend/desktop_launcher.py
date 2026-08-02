from __future__ import annotations

import socket
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

import uvicorn

from app.main import app

READY_TIMEOUT_SECONDS = 30.0
READY_POLL_SECONDS = 0.2
HTTP_REQUEST_TIMEOUT_SECONDS = 1.0


def main() -> None:
    requested_port = int(os.environ.get("SH2_OPTIMIZER_PORT", "8000"))
    port = _choose_port(requested_port)
    url = f"http://127.0.0.1:{port}"
    if os.environ.get("SH2_OPTIMIZER_OPEN_BROWSER", "1") != "0":
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    print("FOSIM - Fastening Optimization & Simulation Manager")
    print(f"Opening {url}")
    print("Close this window to stop the app.")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )


def _choose_port(preferred: int) -> int:
    if _port_available(preferred):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def _wait_for_http_ok(
    url: str,
    timeout_seconds: float = READY_TIMEOUT_SECONDS,
    interval_seconds: float = READY_POLL_SECONDS,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            with urllib.request.urlopen(url, timeout=HTTP_REQUEST_TIMEOUT_SECONDS) as response:
                status = getattr(response, "status", None)
                if status is None:
                    status = response.getcode()
                if 200 <= int(status) < 300:
                    return True
        except (OSError, urllib.error.URLError):
            pass

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(interval_seconds, remaining))


def _open_browser(url: str) -> None:
    health_url = f"{url.rstrip('/')}/api/health"
    if _wait_for_http_ok(health_url):
        webbrowser.open_new_tab(_browser_launch_url(url))
    else:
        print(
            f"Server did not become ready within {READY_TIMEOUT_SECONDS:.0f}s. "
            f"Open {url} after startup finishes."
        )


def _browser_launch_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query.append(("startup", str(int(time.time() * 1000))))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


if __name__ == "__main__":
    main()
