# Stayline desktop app

The desktop launcher starts the existing local HTTP application and presents
it in a native window through `pywebview`. If a platform webview backend is not
available, it opens the same UI in the default browser.

## Setup

### macOS and Linux

From the project root:

```bash
sh desktop/setup-desktop.sh
.venv/bin/python desktop/run_desktop.py
```

On Linux, `pywebview` may require the platform's GTK/WebKit packages. The
launcher still works without them by opening the browser fallback.

### Windows PowerShell

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\desktop\setup-desktop.ps1
.\.venv\Scripts\python.exe desktop\run_desktop.py
```

The default desktop URL is `http://127.0.0.1:8000`. Override it with
`DESKTOP_HOST` and `DESKTOP_PORT`. The desktop launcher uses in-memory storage
by default, so it works immediately after setup. PostgreSQL remains available
through the same `HOTEL_STORAGE=postgres` and `DATABASE_URL` environment
variables documented in the root README.

The included `stayline.desktop` file is a Linux launcher template. Copy it to
`~/.local/share/applications/` after adjusting its `Exec` path to the absolute
path of the extracted project directory.