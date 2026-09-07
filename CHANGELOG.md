# Changelog

All notable changes to theme-gui are documented in this file.
Dates are in YYYY-MM-DD format.

## [0.1.1] - 2026-09-07

### Changed

- **Theming follows hyprtk-bar's settings** — the UI now resolves the bar's
  palette (pywal / imported / manual) exactly like hyprtk-bar, so theme-gui
  matches the bar, menu, and the rest of the desktop regardless of which theme
  source is active. New `bar_theme.py`; `build_app_css()` uses the resolved
  palette (accent follows pywal color5 for imported themes).
- **Live re-theme** — theme-gui re-themes itself when a bar theme is picked in
  the Bar Themes page or the wallpaper changes (shared `refresh_app_css()`
  helper).
- Waybar Themes page replaced with a Bar Themes page managing hyprtk-bar
  (`~/.config/hyprtk-bar/themes/`); all waybar references removed.
- Bar restart on theme apply no longer kills the wrapper shell (pkill pattern
  fix) — the bar comes back reliably after applying a bar theme.
- Relicensed to **GPL-2.0** (was Apache-2.0); full GPL-2.0 text added to
  `LICENSE` and README references updated.

## [0.1.0] - 2026-09-03

Initial release. GTK4/Adwaita theme manager for Hyprland.

### Added

- Wallpaper page: thumbnail grid with cached batch loading, apply / random
  apply, selectable wallpaper directory, refresh of the app CSS on apply
- Pywal Colors page: load color schemes, edit individual colors, re-run `wal`,
  choose the wal output directory
- Rofi Themes page: browse and apply rofi themes
- Bar Themes page: list themes, detect + show the active one, restart the bar
- Matuwall page: manage matuwall wallpaper generation
- Swaylock page: apply themed lock-screen config
- Icons page: switch icon themes
- SDDM & GRUB page: themed login / bootloader settings
- Whole UI re-tinted live from `~/.cache/wal/colors.json` with contrast-aware
  accents
- Atomic config writes, wallpaper thumbnail cache, `install.sh` (install /
  uninstall) with desktop entry and pre-built cache