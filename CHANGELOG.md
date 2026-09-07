# Changelog

All notable changes to theme-gui are documented in this file.
Dates are in YYYY-MM-DD format.

## [Unreleased]

### Changed

- Waybar Themes page replaced with a Bar Themes page managing hyprtk-bar
  (`~/.config/hyprtk-bar/themes/`); all waybar references removed.
- Bar restart on theme apply no longer kills the wrapper shell (pkill pattern
  fix) — the bar comes back reliably after applying a bar theme.

### Changed

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