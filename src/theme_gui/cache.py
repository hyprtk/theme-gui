"""Wallpaper thumbnail cache for fast GUI loading."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf

from . import paths
from .colors import _atomic_write

log = logging.getLogger(__name__)

THUMB_SIZE = (150, 100)
THUMB_DIR = paths.THEME_GUI_CACHE / "thumbnails"
INDEX_FILE = paths.THEME_GUI_CACHE / "wallpaper-index.json"


def _thumb_path(src: Path) -> Path:
    """Deterministic thumbnail path for a given source image."""
    h = hashlib.md5(str(src).encode(), usedforsecurity=False).hexdigest()[:12]
    return THUMB_DIR / f"{h}.png"


def build_index(wallpaper_dir: Path, force: bool = False) -> list[dict]:
    """Scan *wallpaper_dir*, generate thumbnails, return index entries."""
    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    existing: dict[str, dict] = {}
    if INDEX_FILE.exists():
        try:
            for e in json.loads(INDEX_FILE.read_text()):
                existing[e["path"]] = e
        except (json.JSONDecodeError, OSError):
            pass

    images = sorted(
        p for p in wallpaper_dir.iterdir()
        if p.suffix.lower() in paths.IMAGE_EXTS
    )

    index: list[dict] = []
    for img in images:
        key = str(img)
        tp = _thumb_path(img)

        if force or not tp.exists() or _is_stale(img, tp):
            try:
                _generate_thumbnail(img, tp)
            except Exception as exc:
                log.warning("thumb fail %s: %s", img.name, exc)
                continue

        entry = existing.get(key, {})
        entry["path"] = key
        entry["thumb"] = str(tp)
        entry["name"] = img.name
        index.append(entry)

    _atomic_write(INDEX_FILE, json.dumps(index, indent=1))
    return index


def load_index() -> list[dict]:
    """Load cached index or return empty list."""
    if not INDEX_FILE.exists():
        return []
    try:
        return json.loads(INDEX_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def is_valid(wallpaper_dir: Path) -> bool:
    """Check if cache is up-to-date for *wallpaper_dir*."""
    if not INDEX_FILE.exists():
        return False
    idx = load_index()
    if not idx:
        return False
    cached_dirs = {Path(e["path"]).parent for e in idx}
    return wallpaper_dir in cached_dirs


def _is_stale(src: Path, thumb: Path) -> bool:
    return thumb.stat().st_mtime < src.stat().st_mtime


def _generate_thumbnail(src: Path, dest: Path):
    """Create a thumbnail PNG at *dest* from *src*."""
    buf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        str(src), THUMB_SIZE[0], THUMB_SIZE[1], True
    )
    buf.savev(str(dest), "png", [], [])
