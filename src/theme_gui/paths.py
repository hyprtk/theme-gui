from pathlib import Path

HOME = Path.home()

# ── hyprtk-merged source ──────────────────────────────────────
HYPRTK = HOME / "hyprtk"

# ── pywal cache ───────────────────────────────────────────────
WAL_CACHE = HOME / ".cache" / "wal"
WAL_COLORS = WAL_CACHE / "colors"

# ── live configs ──────────────────────────────────────────────
CONFIG = HOME / ".config"
BAR_CONFIG = CONFIG / "hyprtk-bar" / "config.json"
BAR_THEMES = CONFIG / "hyprtk-bar" / "themes"
THEME_STYLE_CACHE = WAL_CACHE.parent / ".themestyle.sh"

ROFI_CONFIG = CONFIG / "rofi"
ROFI_VARIANTS = ROFI_CONFIG / "variants"
ROFI_VARIANT_LINK = ROFI_CONFIG / "variant.rasi"

SWAYLOCK_CONFIG = CONFIG / "swaylock" / "config"
MATUWALL_CONFIG = CONFIG / "matuwall" / "config.json"

# ── hyprtk scripts ────────────────────────────────────────────
HYPRTK_SCRIPTS = HYPRTK / "hypr" / "scripts"
WALLPAPER_COLORS_SH = HYPRTK_SCRIPTS / "wallpaper-colors.sh"
CHANGE_ICONS_SH = HYPRTK / "configs" / "papirus-icons" / "scripts" / "change-icons.sh"
BAR_LAUNCHER = HOME / ".local" / "bin" / "hyprtk-bar"
SYNC_ROFI_SH = HYPRTK / "configs" / "rofi" / "scripts" / "sync-rofi-theme.sh"

# ── wallpaper directories ─────────────────────────────────────
WALLPAPER_DIRS = [
    HOME / "Pictures" / "Wallpapers",
    HOME / "Pictures",
    HYPRTK / "assets" / "Wallpapers",
]

# ── theme-gui own config ──────────────────────────────────────
THEME_GUI_CONFIG = CONFIG / "theme-gui" / "config.json"
THEME_GUI_CACHE = HOME / ".cache" / "theme-gui"

# ── image extensions ──────────────────────────────────────────
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
