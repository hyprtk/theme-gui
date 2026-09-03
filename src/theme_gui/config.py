"""Theme-gui configuration with atomic writes."""
from __future__ import annotations

import json
from pathlib import Path

from . import paths
from .colors import _atomic_write

_DEFAULTS = {
    "last_page": "wallpaper",
    "window_width": 1100,
    "window_height": 700,
    "wallpaper_dir": str(Path.home() / "Pictures" / "Wallpapers"),
    "pywal_backend": "wal",
}


def _ensure():
    paths.THEME_GUI_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if not paths.THEME_GUI_CONFIG.exists():
        _atomic_write(paths.THEME_GUI_CONFIG, json.dumps(_DEFAULTS, indent=2))


def load() -> dict:
    _ensure()
    try:
        data = json.loads(paths.THEME_GUI_CONFIG.read_text())
    except (json.JSONDecodeError, OSError):
        data = {}
    return {**_DEFAULTS, **data}


def save(data: dict):
    _ensure()
    _atomic_write(paths.THEME_GUI_CONFIG, json.dumps(data, indent=2))
