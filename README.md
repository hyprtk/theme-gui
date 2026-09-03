# theme-gui

A GTK4/Adwaita theme manager for the Hyprland desktop, written in Python. It
gives you a single window to pick a wallpaper, regenerate pywal colors, and
apply matching themes across rofi, waybar, swaylock, icons, and SDDM/GRUB —
all tinted with your active pywal palette.

## Features

- **Wallpaper** — thumbnail grid with cached batch loading, apply any wallpaper,
  or pick a random one from your collection; choose the wallpaper directory
- **Pywal Colors** — load pywal color schemes, tweak individual colors, re-run
  `wal` on your wallpaper, and rebuild the cache
- **Rofi Themes** — browse and apply rofi themes
- **Waybar Themes** — list installed waybar themes, see the active one, and
  apply/launch from the GUI
- **Matuwall** — manage matuwall wallpaper generation
- **Swaylock** — apply themed lock-screen config
- **Icons** — switch icon themes
- **SDDM & GRUB** — themed login / bootloader settings
- **Live pywal theming** — the whole UI is re-tinted from
  `~/.cache/wal/colors.json` with contrast-aware accents (color5/color6)

## Install

```bash
./install.sh
# uninstall
./install.sh --uninstall
```

Installs a venv + launcher to `~/.local/share/theme-gui/` and
`~/.local/bin/theme-gui`, installs the `hyprtk-themer` desktop entry, and
pre-builds the wallpaper thumbnail cache from `~/Pictures/Wallpapers`.

## Usage

```bash
theme-gui          # launch the GUI
hyprtk-themer      # alias desktop launcher
```

## Configuration

`~/.config/theme-gui/config.json` (auto-created):

```json
{
  "last_page": "wallpaper",
  "window_width": 1100,
  "window_height": 700,
  "wallpaper_dir": "/home/user/Pictures/Wallpapers",
  "pywal_backend": "wal"
}
```

## Requirements

- python3, python-gobject (PyGObject), pycairo
- gtk4, libadwaita
- pywal16 (and the target tools: rofi, waybar, swaylock, sddm, matuwall)

## Structure

```
src/theme_gui/
├── app.py        # GTK4/Adwaita window, page registry, pywal CSS
├── colors.py     # wal color parsing + contrast helpers
├── config.py     # config persistence (atomic writes)
├── cache.py      # wallpaper thumbnail index
├── paths.py      # app paths
└── modules/      # one page per target (wallpaper, pywal, rofi, waybar,
                  # matuwall, swaylock, icons, sddm)
```

## License

GPL-2.0.