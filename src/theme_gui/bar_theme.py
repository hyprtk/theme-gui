"""Resolve hyprtk-bar's theme palette so theme-gui follows the bar.

theme-gui's UI is themed from the bar's configured theme source (pywal |
imported | manual) exactly like hyprtk-bar resolves it, so the app matches the
bar and the rest of the desktop regardless of which source is active.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from . import paths
from .colors import is_valid_hex, parse_wal_colors

log = logging.getLogger(__name__)

DEFAULT_BG = "#1a1b26"
DEFAULT_FG = "#c0caf5"
DEFAULT_ACCENT = "#7aa2f7"


def load_bar_theme() -> dict:
    """The bar's ``theme`` block (source + theme_name + manual colors).

    Returns ``{}`` when the bar config can't be read. Mirrors the bar's theming
    source so theme-gui shares the same palette.
    """
    try:
        data = json.loads(paths.BAR_CONFIG.read_text())
    except (OSError, ValueError):
        return {}
    theme = data.get("theme")
    return theme if isinstance(theme, dict) else {}


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) >= 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha:.2f})"
    return hex_color


def _theme_css(theme_dir: Path) -> str:
    """Read a theme's CSS (resolving imports best-effort) for palette parsing."""
    css = ""
    if (theme_dir / "style.css").is_file():
        css = (theme_dir / "style.css").read_text(errors="ignore")
    return css


def _find_block(css: str, selector: str) -> str | None:
    idx = css.find(selector)
    if idx < 0:
        return None
    brace = css.find("{", idx)
    if brace < 0:
        return None
    depth = 0
    for i in range(brace, len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[brace + 1:i]
    return None


def _resolve_value(value: str, wal: dict[str, str]) -> str | None:
    """Resolve a CSS color token (@colorN / rgba / hex) to a hex color.

    rgba() colors are kept as their rgb part (alpha handled by the GTK theme
    itself); solid hex is returned as-is.
    """
    m = re.match(r"@color(\d+)", value, re.I)
    if m and wal:
        hex_color = wal.get(f"color{m.group(1)}")
        if hex_color:
            return hex_color
    m = re.search(r"#([0-9a-fA-F]{6,8})", value)
    if m:
        return "#" + m.group(1)
    m = re.search(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)", value, re.I)
    if m:
        r, g, b = (int(float(m.group(i))) for i in (1, 2, 3))
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def _import_theme_palette(theme: dict, wal: dict[str, str]) -> dict | None:
    """Parse the bar's selected imported theme into bg/fg/accent, or None."""
    name = theme.get("theme_name")
    if not name:
        return None
    theme_dir = paths.BAR_THEMES / Path(name).name
    css = _theme_css(theme_dir)
    if not css:
        return None
    block = _find_block(css, "window#waybar") or _find_block(css, "window #waybar")
    if block is None:
        block = css
    background = foreground = None
    for prop, out in (
        (r"background\s*:\s*([^;]+)", "background"),
        (r"color\s*:\s*([^;]+)", "foreground"),
    ):
        m = re.search(prop, block)
        if m:
            val = _resolve_value(m.group(1), wal)
            if val and is_valid_hex(val):
                if out == "background":
                    background = val
                else:
                    foreground = val
    if background or foreground:
        # The accent for an imported theme follows the live pywal color5 (like
        # hyprtk-bar overlays its imports), falling back to the theme bg.
        accent = wal.get("color5") or wal.get("color4") or background
        return {
            "background": background or DEFAULT_BG,
            "foreground": foreground or DEFAULT_FG,
            "accent": accent or DEFAULT_ACCENT,
        }
    return None


def resolve_palette() -> dict:
    """Resolve the theme-gui palette from the bar's theme.source.

    Returns ``background``/``foreground``/``accent`` plus a ``dark`` flag for
    the UI — the same palette hyprtk-bar builds.
    """
    theme = load_bar_theme()
    source = theme.get("source", "pywal")
    palette = {
        "background": theme.get("background", DEFAULT_BG),
        "foreground": theme.get("foreground", DEFAULT_FG),
        "accent": theme.get("accent", DEFAULT_ACCENT),
    }

    wal = parse_wal_colors()

    if source == "manual":
        return palette

    if source == "imported":
        imported = _import_theme_palette(theme, wal)
        if imported is not None:
            return imported

    # pywal (also the fallback when an imported theme fails)
    if wal:
        palette["background"] = wal.get("background") or palette["background"]
        palette["foreground"] = wal.get("foreground") or palette["foreground"]
        palette["accent"] = wal.get("color5") or wal.get("color4") or palette["accent"]

    return palette