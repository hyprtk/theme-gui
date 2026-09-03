"""Color utilities and config helpers for theme-gui."""
from __future__ import annotations

from pathlib import Path

from . import paths

# ── Color conversion helpers ────────────────────────────────────────────────


def is_valid_hex(hex_color: str) -> bool:
    """Return True if *hex_color* is a valid #RRGGBB or #RRGGBBAA color."""
    if not isinstance(hex_color, str):
        return False
    h = hex_color.strip().lstrip("#")
    return len(h) in (6, 8) and all(c in "0123456789abcdefABCDEF" for c in h)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB or #RRGGBBAA to (r, g, b) ints 0-255.

    Returns (0, 0, 0) for invalid input instead of raising.
    """
    h = hex_color.strip().lstrip("#")
    if len(h) >= 6:
        try:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            pass
    return 0, 0, 0


def hex_to_rgb_float(hex_color: str) -> tuple[float, float, float]:
    """Convert #RRGGBB to (r, g, b) floats 0.0-1.0."""
    r, g, b = hex_to_rgb(hex_color)
    return r / 255, g / 255, b / 255


def hex_to_rgba(hex_color: str, alpha: int = 255) -> str:
    """Convert #RRGGBB or #RRGGBBAA to rgba() string."""
    r, g, b = hex_to_rgb(hex_color)
    h = hex_color.lstrip("#")
    if len(h) == 8:
        a = int(h[6:8], 16)
    else:
        a = alpha
    return f"rgba({r},{g},{b},{a / 255:.2f})"


def rgba_to_hex(red: float, green: float, blue: float, alpha: float = 1.0) -> str:
    """Convert GDK RGBA floats to #RRGGBB or #RRGGBBAA."""
    r = int(red * 255)
    g = int(green * 255)
    b = int(blue * 255)
    a = int(alpha * 255)
    if a < 255:
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_gdk_rgba(hex_color: str) -> str:
    """Convert #RRGGBB to #RRGGBBFF (GDK4 format)."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        return f"#{h}FF"
    return hex_color


def strip_hex_alpha(hex_color: str) -> str:
    """Remove alpha from hex: #RRGGBBAA -> #RRGGBB."""
    h = hex_color.lstrip("#")
    if len(h) == 8:
        return f"#{h[:6]}"
    return hex_color


def contrast_fg(hex_bg: str) -> str:
    """Return black or white for best contrast against *hex_bg*.

    Uses the WCAG relative luminance formula for accurate contrast ratio.
    """
    r, g, b = hex_to_rgb(hex_bg)
    # linearize sRGB
    def _linear(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)
    return "#000000" if luminance > 0.179 else "#ffffff"


def get_color_name(index: int) -> str:
    names = [
        "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
        "bright-black", "bright-red", "bright-green", "bright-yellow",
        "bright-blue", "bright-magenta", "bright-cyan", "bright-white",
    ]
    return names[index] if 0 <= index < len(names) else f"color{index}"


# ── Pywal color parsing ────────────────────────────────────────────────────


def parse_wal_colors() -> dict[str, str]:
    """Parse ~/.cache/wal/colors.sh into {color0..color15, background, foreground, ...}."""
    result: dict[str, str] = {}
    wal_sh = paths.WAL_CACHE / "colors.sh"
    wal_file = wal_sh if wal_sh.exists() else paths.WAL_COLORS
    if not wal_file.exists():
        return result
    for line in wal_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            val = val.strip().strip("'\"")
            if is_valid_hex(val):
                result[key.strip()] = val
    return result


# ── Config I/O helpers ─────────────────────────────────────────────────────


def read_swaylock_config() -> dict[str, str]:
    """Parse swaylock config into {key: value} dict."""
    result: dict[str, str] = {}
    if not paths.SWAYLOCK_CONFIG.exists():
        return result
    for line in paths.SWAYLOCK_CONFIG.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            result[key.strip()] = val.strip()
    return result


def write_swaylock_config(data: dict[str, str]):
    """Write swaylock config from dict (atomic write)."""
    paths.SWAYLOCK_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={val}" for key, val in data.items()]
    _atomic_write(paths.SWAYLOCK_CONFIG, "\n".join(lines) + "\n")


# ── Atomic file write ──────────────────────────────────────────────────────


def _atomic_write(path: Path, content: str):
    """Write *content* to *path* atomically via temp file + rename."""
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content.encode())
        os.fsync(fd)
        os.close(fd)
        os.rename(tmp, str(path))
    except BaseException:
        os.close(fd) if not os.get_inheritable(fd) else None
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
