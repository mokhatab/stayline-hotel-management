"""Launch Stayline as a local desktop-style application.

If pywebview is installed, the local HTTP UI opens in a native window.
Otherwise the default browser opens, which keeps the launcher usable on
systems without a native webview backend.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
HOST = os.environ.get("DESKTOP_HOST", "127.0.0.1")
PORT = int(os.environ.get("DESKTOP_PORT", "8000"))
URL = f"http://{HOST}:{PORT}"


def wait_for_server(url: str, timeout_seconds: float = 20) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1):
                return
        except (OSError, URLError):
            time.sleep(0.2)
    raise RuntimeError(f"Stayline did not start within {timeout_seconds:g} seconds")


def start_server() -> subprocess.Popen:
    environment = os.environ.copy()
    environment.setdefault("PYTHONPATH", str(ROOT / "src"))
    environment["HOST"] = HOST
    environment["PORT"] = str(PORT)
    environment.setdefault("HOTEL_STORAGE", "memory")
    return subprocess.Popen(
        [sys.executable, "-m", "hotel_management"],
        cwd=ROOT,
        env=environment,
    )


def open_window() -> None:
    try:
        import webview
    except ImportError:
        print("pywebview is not installed; opening the default browser instead.")
        webbrowser.open(URL)
        return

    webview.create_window(
        "Stayline Hotel Management",
        URL,
        width=1280,
        height=840,
        min_size=(960, 640),
    )
    webview.start()


def main() -> int:
    server = start_server()
    try:
        wait_for_server(URL)
        print(f"Stayline desktop app is running at {URL}")
        open_window()
        if "webview" not in sys.modules:
            server.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())