from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    """Return the root for bundled resources in dev or PyInstaller builds."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[3]


def frontend_dist_path() -> Path:
    return resource_root() / "frontend" / "dist"


def runtime_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parents[3]
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
