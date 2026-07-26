from __future__ import annotations

import socket
import os
import threading
import time
import webbrowser

import uvicorn

from app.main import app


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


def _open_browser(url: str) -> None:
    time.sleep(1.2)
    webbrowser.open(url)


if __name__ == "__main__":
    main()
