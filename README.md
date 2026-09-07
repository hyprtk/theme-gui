# theme-gui

A GTK3 theme manager for the Hyprland desktop, written in Python. It gives you
a single window to pick a wallpaper, regenerate pywal colors, and apply
matching themes across rofi, the hyprtk-bar, swaylock, icons, and SDDM/GRUB —
all themed with the same palette resolution as hyprtk-bar (pywal / imported /
manual) and rendered as a frameless glass panel that matches the bar's system
monitor look and feel.

## Features

- **Wallpaper** — thumbnail grid with cached batch loading, apply any wallpaper,
  or pick a random one from your collection; choose the wallpaper directory
- **Pywal Colors** — load pywal color schemes, tweak individual colors, re-run
  `wal` on your wallpaper, and rebuild the cache
- **Rofi Themes** — browse and apply rofi themes
- **Bar Themes** — list installed hyprtk-bar themes, see the active one, and
  apply / restart the bar from the GUI
- **Matuwall** — manage matuwall wallpaper generation
- **Swaylock** — apply themed lock-screen config
- **Icons** — switch icon themes
- **SDDM & GRUB** — themed login / bootloader settings
- **Monitor-style glass UI** — frameless, translucent, rounded window with a
  Nerd-Font glyph sidebar (active row = accent), matching the hyprtk-bar system
  monitor / settings-dialogue look. Live re-theme from the bar's theme source.

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

- python3, python-gobject (PyGObject, GTK3 bindings), pycairo
- gtk3
- pywal16 (and the target tools: rofi, hyprtk-bar, swaylock, sddm, matuwall)

## Structure

```
src/theme_gui/
├── app.py        # frameless glass window, glyph sidebar + page stack
├── theme.py      # palette resolution + GTK3 chrome CSS (mc-* / settings-*)
├── bar_theme.py  # hyprtk-bar palette resolver (pywal / imported / manual)
├── colors.py     # wal color parsing + contrast helpers
├── config.py     # config persistence (atomic writes)
├── cache.py      # wallpaper thumbnail index
├── paths.py      # app paths
├── widgets/      # Glyph, BasePage, sections, color swatches + grid
└── modules/      # one page per target (wallpaper, pywal, rofi, bar,
                  # matuwall, swaylock, icons, sddm)
```

## License

GPL-2.0.