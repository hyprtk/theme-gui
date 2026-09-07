# Changelog

All notable changes to theme-gui are documented in this file.
Dates are in YYYY-MM-DD format.

## [0.2.0] - 2026-09-07

### Changed

- **Rewritten as a GTK3 glass window** — full port from GTK4/Adwaita to GTK3 so
  theme-gui matches the hyprtk-bar ecosystem (the bar, menu, and arc-menu are
  all GTK3). The window is now frameless, translucent and rounded (`.popup-box`)
  like the bar's system monitor and settings dialogue, with a draggable header,
  `mc-*` chrome and in-window toasts replacing the Adw.Toast overlay.
- **Navigation** — the sidebar is now the monitor's glyph+label language
  (Nerd Font glyphs from `Symbols Nerd Font`, active row filled with the theme
  accent) driving a crossfade stack of the same eight pages.
- **Theming** — new `theme.py` resolves the bar palette (pywal / imported /
  manual via `bar_theme.py`) and emits GTK3 CSS scoped to the app subtree
  (`.tg-app`) using the monitor's `.popup-box` / `.mc-*` / `.settings-*` class
  vocabulary; standard GTK3 widgets (entries, switches, scales, colour
  swatches, flow-box tiles) get matching translucent styling. Live re-theme on
  bar-theme pick and wallpaper change is preserved.
- **Page styling** — every module (wallpaper, pywal, rofi, bar, matuwall,
  swaylock, icons, sddm) rebuilt with glass `settings-section` cards, list rows
  with Active badges, circular colour swatches via GTK3 `ColorChooserDialog`,
  and the swaylock preview ported to the GTK3 `draw` signal.
- `__main__.py` sets the prgname so the Wayland window class stays
  `dev.hyprtk.theme_gui` (Hyprland float + size windowrule still applies).

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