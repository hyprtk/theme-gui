"""Theme-gui GTK3 chrome theming from the hyprtk-bar palette.

Resolves the bar's theme source (pywal | imported | manual) exactly like
hyprtk-bar does and emits GTK3 CSS for the whole app using the bar's monitor /
settings-dialogue class vocabulary (``.popup-box``, ``.mc-*``, ``.settings-*``)
so theme-gui matches the bar's system monitor look and re-themes live.
"""
from __future__ import annotations

import re

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gdk, Gtk  # noqa: E402

from .bar_theme import resolve_palette  # noqa: E402
from .colors import parse_wal_colors  # noqa: E402

DEFAULT_BG = "#1a1b26"
DEFAULT_FG = "#c0caf5"
DEFAULT_ACCENT = "#7aa2f7"

# Per-page accent drawn from the pywal palette (matching the monitor's colour
# assignments so each module reads distinctly). Falls back to the bar accent.
PAGE_PYWAL_KEYS = {
    "wallpaper": "color5",
    "pywal": "color4",
    "rofi": "color6",
    "bar": "color2",
    "matuwall": "color3",
    "swaylock": "color6",
    "icons": "color4",
    "sddm": "color5",
}

_CSS_PROVIDER: Gtk.CssProvider | None = None


def _rgba(hex_color: str, alpha: float) -> str:
    """Convert a #rgb/#rrggbb/#rrggbbaa/rgba()/rgb() color to rgba()."""
    color = (hex_color or "").strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", color)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 8:
            r, g, b, a = (int(h[i:i + 2], 16) for i in (0, 2, 4, 6))
            return f"rgba({r}, {g}, {b}, {a / 255:.2f})"
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha:.2f})"
    m = re.search(r"rgba?\(([^)]+)\)", color, re.I)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        try:
            r, g, b = (int(float(parts[i])) for i in (0, 1, 2))
            return f"rgba({r}, {g}, {b}, {alpha:.2f})"
        except (ValueError, IndexError):
            return color
    return color


def _hex_of(color: str, fallback: str) -> str:
    """Return a #rrggbb form of a color (strip alpha/rgba), best effort."""
    color = (color or "").strip()
    m = re.search(r"#([0-9a-fA-F]{6})", color)
    if m:
        return "#" + m.group(1)
    m = re.search(r"rgba?\(([^)]+)\)", color, re.I)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        try:
            r, g, b = (int(float(parts[i])) for i in (0, 1, 2))
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            pass
    return fallback


def contrast_fg(hex_bg: str) -> str:
    """Black/white that contrasts with the hex background (simple luminance)."""
    h = hex_bg.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) < 6:
        return "#ffffff"
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return "#ffffff"
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#000000" if luminance > 150 else "#ffffff"


def resolve_page_accent(page: str, accent: str) -> str:
    """The accent colour a given module/page uses (pywal or the bar accent)."""
    pywal = parse_wal_colors()
    key = PAGE_PYWAL_KEYS.get(page)
    return (pywal.get(key) if key else None) or accent


def build_css(palette: dict | None = None) -> str:
    """Full GTK3 CSS for theme-gui from the bar palette (or a fresh resolve).

    Classes mirror the bar's monitor/settings vocabulary so the app shares the
    bar's look; standard widgets are themed only inside the app's own subtree
    (``.tg-app``) so native GTK dialogs keep their normal appearance.
    """
    if palette is None:
        palette = resolve_palette()
    pywal = parse_wal_colors()

    bg = _hex_of(palette.get("background") or DEFAULT_BG, DEFAULT_BG)
    fg = _hex_of(palette.get("foreground") or DEFAULT_FG, DEFAULT_FG)
    accent = _hex_of(palette.get("accent") or DEFAULT_ACCENT, DEFAULT_ACCENT)
    on_accent = contrast_fg(accent)
    hover = _rgba(fg, 0.10)
    panel = _rgba(fg, 0.045)
    line = _rgba(fg, 0.16)
    muted = _rgba(fg, 0.65)
    glass_alpha = 0.82

    return f"""
/* ── app glass window ─────────────────────────────────────── */
.popup-box {{
  background-color: {_rgba(bg, glass_alpha)};
  border: 1px solid {_rgba(accent, 0.45)};
  border-radius: 14px;
  color: {fg};
}}
.tg-app, .tg-app label {{ color: {fg}; }}

/* ── header (mc-title / mc-close) ─────────────────────────── */
.mc-title {{ font-weight: bold; font-size: 15px; }}
.mc-close {{ min-width: 22px; min-height: 22px; padding: 0 4px;
            border-radius: 6px; color: {fg}; background: transparent; }}
.mc-close:hover {{ background-color: {hover}; }}

/* ── sidebar + pages ──────────────────────────────────────── */
.mc-sidebar {{ padding: 4px; border-radius: 8px;
               background-color: {_rgba(fg, 0.05)}; }}
.mc-sidebar-button {{ padding: 6px 10px; border-radius: 6px;
                     background: transparent; border: none; }}
.mc-sidebar-button:hover {{ background-color: {hover}; }}
.mc-sidebar-button.active {{ background-color: {accent};
                            color: {on_accent}; }}
.mc-sidebar-label {{ font-size: 13px; }}
.mc-icon {{ color: {accent}; }}
.mc-sidebar-button.active .mc-icon {{ color: {on_accent}; }}
.mc-page-title {{ font-weight: bold; font-size: 16px;
                  padding-bottom: 2px; }}

/* ── generic widgets inside the app subtree ───────────────── */
.tg-app button {{ color: {fg}; background-color: {_rgba(fg, 0.05)};
                  border: 1px solid {_rgba(fg, 0.10)};
                  border-radius: 6px; padding: 4px 10px; }}
.tg-app button:hover {{ background-color: {hover}; }}
.tg-app button:active {{ background-color: {_rgba(accent, 0.25)}; }}
.tg-app button:disabled {{ opacity: 0.45; }}
.tg-app button.settings-apply {{ background-color: {accent};
    color: {on_accent}; border: none; font-weight: bold; }}
.tg-app button.settings-apply:hover {{ background-color: {_rgba(accent, 0.85)}; }}
.tg-app button.settings-apply:disabled {{ background-color: {_rgba(accent, 0.45)}; }}
.tg-app button.flat {{ background-color: transparent; border: none; }}
.tg-app button.flat:hover {{ background-color: {hover}; }}

.tg-app entry, .tg-app spinbutton {{
  color: {fg};
  background-color: {_rgba(fg, 0.07)};
  border: 1px solid {_rgba(fg, 0.18)};
  border-radius: 6px;
  padding: 3px 6px;
}}
.tg-app entry:focus, .tg-app spinbutton:focus {{ border-color: {accent};
    box-shadow: none; }}
.tg-app spinbutton button {{ padding: 0 4px; }}

.tg-app checkbutton, .tg-app radiobutton {{ color: {fg}; }}
.tg-app checkbutton check, .tg-app radiobutton radio {{
  min-width: 16px; min-height: 16px; }}
.tg-app checkbutton check:checked {{
  background-color: {accent}; border-color: {accent}; }}
.tg-app radiobutton radio:checked {{
  border-color: {accent}; }}

/* switch: track + slider */
.tg-app switch {{
  background-color: {_rgba(fg, 0.22)};
  border-radius: 12px; min-width: 40px; min-height: 20px; }}
.tg-app switch slider {{
  background-color: {fg};
  border-radius: 9px; min-width: 16px; min-height: 16px;
  margin: 2px; }}
.tg-app switch:checked {{ background-color: {accent}; }}
.tg-app switch:checked slider {{ background-color: {on_accent}; }}

/* scale */
.tg-app scale trough {{ background-color: {_rgba(fg, 0.22)};
  border-radius: 3px; min-height: 4px; }}
.tg-app scale highlight {{ background-color: {accent}; border-radius: 3px; }}
.tg-app scale slider {{ background-color: {fg}; border-radius: 6px;
  min-width: 12px; min-height: 12px; }}

/* ── sections / cards ─────────────────────────────────────── */
.settings-section {{
  background-color: {_rgba(fg, 0.04)};
  border: 1px solid {_rgba(fg, 0.08)};
  border-radius: 10px;
  padding: 10px;
}}
.settings-section-title {{ font-size: 11px; font-weight: bold;
  opacity: 0.8; letter-spacing: 0.4px; }}
.tg-app .heading {{ font-weight: bold; font-size: 14px; }}

/* ── generic rows / lists / tiles ─────────────────────────── */
.tg-row {{ padding: 6px 10px; border-radius: 8px; }}
.tg-row:hover {{ background-color: {hover}; }}
.tg-row.active {{ background-color: {_rgba(accent, 0.16)};
  border: 1px solid {_rgba(accent, 0.6)}; }}
.tg-row .badge {{ font-size: 10px; font-weight: bold;
  color: {on_accent}; background-color: {accent};
  border-radius: 8px; padding: 1px 7px; }}

.thumb-tile {{ background-color: {_rgba(fg, 0.05)};
  border: 2px solid transparent; border-radius: 10px; padding: 0; }}
.thumb-tile:hover {{ background-color: {hover}; }}
.thumb-tile.selected {{ border-color: {accent}; }}

.preview-frame {{ background-color: {_rgba(fg, 0.04)};
  border: 1px solid {_rgba(fg, 0.10)}; border-radius: 10px; }}

.dim-label {{ opacity: 0.65; }}
.mc-unavailable {{ font-size: 12px; opacity: 0.7; }}
.loading-spinner {{ color: {accent}; }}
separator {{ background-color: {_rgba(fg, 0.12)}; }}

/* color swatch buttons */
.color-swatch {{ border: 1px solid {_rgba(fg, 0.2)};
  border-radius: 50%; padding: 0; }}
.color-swatch:hover {{ border-color: {fg}; }}

/* in-window toast */
.toast-label {{
  background-color: {_rgba(accent, 0.92)};
  color: {on_accent};
  border-radius: 8px;
  padding: 6px 14px;
  font-weight: bold;
}}

/* swaylock ring preview + focus outline */
focus {{ outline-color: {accent}; }}
treeview.view {{ color: {fg}; }}
"""


def load_css_provider() -> Gtk.CssProvider:
    """Return the (singleton) app CSS provider, loaded with current CSS."""
    global _CSS_PROVIDER
    if _CSS_PROVIDER is None:
        _CSS_PROVIDER = Gtk.CssProvider()
    _CSS_PROVIDER.load_from_data(build_css().encode())
    return _CSS_PROVIDER


def refresh_app_css() -> None:
    """Re-resolve the palette and reload the app CSS (live re-theme)."""
    provider = load_css_provider()
    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )
