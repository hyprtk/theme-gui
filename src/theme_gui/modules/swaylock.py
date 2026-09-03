"""Swaylock theme editor with live preview."""
from __future__ import annotations

import shutil
from pathlib import Path

from gi.repository import Adw, Gtk

from .. import paths
from ..colors import hex_to_rgb_float, read_swaylock_config, write_swaylock_config
from ..widgets import BasePage, show_toast
from ..widgets.color_button import ColorButton


class SwaylockPreview(Gtk.DrawingArea):
    """Live preview of the swaylock indicator wheel using Cairo."""

    def __init__(self):
        super().__init__()
        self.set_size_request(200, 200)
        self.set_vexpand(False)
        self.set_halign(Gtk.Align.CENTER)
        self._colors = {
            "ring-color": "#ffffff",
            "inside-color": "#000000",
            "key-hl-color": "#22d3ee",
            "text-color": "#ffffff",
            "bs-hl-color": "#ff0000",
        }
        self._indicator_radius = 100
        self._indicator_thickness = 18
        self.set_draw_func(self._draw)

    def update_colors(self, colors: dict[str, str]):
        self._colors.update(colors)
        self.queue_draw()

    def set_dimensions(self, radius: int, thickness: int):
        self._indicator_radius = radius
        self._indicator_thickness = thickness
        self.queue_draw()

    def _draw(self, area, cr, width, height):
        import cairo

        cx, cy = width / 2, height / 2
        radius = min(self._indicator_radius, min(width, height) / 2 - 8)

        # outer ring
        r, g, b = hex_to_rgb_float(self._colors.get("ring-color", "#ffffff"))
        cr.set_source_rgb(r, g, b)
        cr.arc(cx, cy, radius, 0, 2 * 3.14159)
        cr.set_line_width(self._indicator_thickness * 0.9)
        cr.stroke()

        # inner circle
        r, g, b = hex_to_rgb_float(self._colors.get("inside-color", "#000000"))
        cr.set_source_rgb(r, g, b)
        cr.arc(cx, cy, radius * 0.72, 0, 2 * 3.14159)
        cr.fill()

        # key highlight dot (at 12 o'clock)
        r, g, b = hex_to_rgb_float(self._colors.get("key-hl-color", "#22d3ee"))
        cr.set_source_rgb(r, g, b)
        dot_r = radius * 0.08
        cr.arc(cx, cy - radius * 0.91, dot_r, 0, 2 * 3.14159)
        cr.fill()

        # backspace highlight dot (at 6 o'clock)
        r, g, b = hex_to_rgb_float(self._colors.get("bs-hl-color", "#ff0000"))
        cr.set_source_rgb(r, g, b)
        cr.arc(cx, cy + radius * 0.91, dot_r, 0, 2 * 3.14159)
        cr.fill()

        # centered text
        r, g, b = hex_to_rgb_float(self._colors.get("text-color", "#ffffff"))
        cr.set_source_rgb(r, g, b)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(radius * 0.35)
        ext = cr.text_extents("Password")
        cr.move_to(cx - ext.width / 2, cy + ext.height / 3)
        cr.show_text("Password")


class SwaylockPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Swaylock", **kwargs)

        # pywal mode section
        wal_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        wal_title = Gtk.Label(label="Pywal Mode")
        wal_title.add_css_class("heading")
        wal_title.set_xalign(0)
        wal_frame.append(wal_title)

        wal_desc = Gtk.Label(
            label="Copy pywal-generated colors to swaylock config. "
            "This syncs the lock screen with your current wallpaper palette."
        )
        wal_desc.set_xalign(0)
        wal_desc.set_wrap(True)
        wal_frame.append(wal_desc)

        apply_wal_btn = Gtk.Button(label="Apply Pywal Colors")
        apply_wal_btn.add_css_class("suggested-action")
        apply_wal_btn.connect("clicked", self._apply_pywal)
        wal_frame.append(apply_wal_btn)
        self._box.append(wal_frame)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self._box.append(sep)

        # manual mode section
        manual_title = Gtk.Label(label="Manual Color Editor")
        manual_title.add_css_class("heading")
        manual_title.set_xalign(0)
        self._box.append(manual_title)

        # refresh from pywal button
        refresh_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        load_pywal_btn = Gtk.Button(label="Load Current Pywal Colors")
        load_pywal_btn.add_css_class("flat")
        load_pywal_btn.connect("clicked", self._load_pywal_colors)
        refresh_box.append(load_pywal_btn)
        self._box.append(refresh_box)

        self._color_buttons: dict[str, ColorButton] = {}

        manual_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        self._preview = SwaylockPreview()
        self._preview.set_valign(Gtk.Align.START)
        manual_row.append(self._preview)

        color_fields = [
            ("ring-color", "Ring (idle)"),
            ("ring-clear-color", "Ring (clear)"),
            ("ring-wrong-color", "Ring (wrong)"),
            ("ring-ver-color", "Ring (verifying)"),
            ("ring-caps-lock-color", "Ring (caps lock)"),
            ("inside-color", "Inside (idle)"),
            ("inside-clear-color", "Inside (clear)"),
            ("inside-wrong-color", "Inside (wrong)"),
            ("inside-ver-color", "Inside (verifying)"),
            ("key-hl-color", "Key highlight"),
            ("text-color", "Text"),
            ("bs-hl-color", "Backspace highlight"),
        ]

        mid = len(color_fields) // 2
        for group in (color_fields[:mid], color_fields[mid:]):
            grid = Gtk.Grid()
            grid.set_column_spacing(12)
            grid.set_row_spacing(6)
            grid.set_valign(Gtk.Align.START)
            for i, (key, label) in enumerate(group):
                lbl = Gtk.Label(label=label)
                lbl.set_xalign(0)
                lbl.set_size_request(130, -1)
                grid.attach(lbl, 0, i, 1, 1)
                cb = ColorButton()
                cb.connect_color_changed(lambda btn, hex_val, k=key: self._on_color_change(k, hex_val))
                self._color_buttons[key] = cb
                grid.attach(cb, 1, i, 1, 1)
            manual_row.append(grid)

        self._box.append(manual_row)

        save_btn = Gtk.Button(label="Save Manual Config")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._save_manual)
        self._box.append(save_btn)

        # settings section
        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self._box.append(sep2)

        settings_title = Gtk.Label(label="Indicator Settings")
        settings_title.add_css_class("heading")
        settings_title.set_xalign(0)
        self._box.append(settings_title)

        self._indicator_radius = Adw.EntryRow(title="Indicator Radius")
        self._indicator_thickness = Adw.EntryRow(title="Indicator Thickness")
        self._fade_in = Adw.EntryRow(title="Fade-in (seconds)")
        self._effect = Adw.EntryRow(title="Effect (e.g. effect-pixelate=5)")
        self._box.append(self._indicator_radius)
        self._box.append(self._indicator_thickness)
        self._box.append(self._fade_in)
        self._box.append(self._effect)

        save_settings_btn = Gtk.Button(label="Save Settings")
        save_settings_btn.add_css_class("suggested-action")
        save_settings_btn.connect("clicked", self._save_settings)
        self._box.append(save_settings_btn)

        self._load()
        self.connect("map", lambda w: self._load())

    def _load(self):
        # Read from saved config first
        config = read_swaylock_config()

        # Also read current pywal colors from main file
        wal_colors_file = paths.WAL_CACHE / "colors"
        if wal_colors_file.exists():
            try:
                hex_colors = []
                for line in wal_colors_file.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("#") and len(line) == 7:
                        hex_colors.append(line[1:].upper())
                
                if len(hex_colors) >= 8:
                    # Map pywal colors to swaylock keys
                    wal_map = {
                        "ring-color": hex_colors[6],           # cyan
                        "ring-clear-color": hex_colors[4],     # blue
                        "ring-wrong-color": hex_colors[1],     # red
                        "ring-ver-color": hex_colors[5],       # magenta
                        "ring-caps-lock-color": hex_colors[5], # magenta
                        "inside-color": hex_colors[0],         # black
                        "inside-clear-color": hex_colors[4],   # blue
                        "inside-wrong-color": hex_colors[1],   # red
                        "inside-ver-color": hex_colors[5],     # magenta
                        "key-hl-color": hex_colors[6],         # cyan
                        "text-color": hex_colors[7],           # white
                        "bs-hl-color": hex_colors[1],          # red
                    }
                    config.update(wal_map)
            except OSError:
                pass

        preview_colors = {}
        for key, cb in self._color_buttons.items():
            val = config.get(key, "#ffffff")
            if not val.startswith("#"):
                val = f"#{val}"
            cb.set_color(val)
            preview_colors[key] = val

        self._preview.update_colors(preview_colors)

        self._indicator_radius.set_text(config.get("indicator-radius", "200"))
        self._indicator_thickness.set_text(config.get("indicator-thickness", "20"))
        self._fade_in.set_text(config.get("fade-in", "1"))

        try:
            r = int(config.get("indicator-radius", "200"))
        except ValueError:
            r = 200
        try:
            t = int(config.get("indicator-thickness", "20"))
        except ValueError:
            t = 20
        self._preview.set_dimensions(r, t)

        for key in config:
            if key.startswith("effect-"):
                self._effect.set_text(f"{key}={config[key]}")
                break

    def _on_color_change(self, key: str, hex_val: str):
        self._preview.update_colors({key: hex_val})

    def _load_pywal_colors(self, btn):
        """Read current pywal colors and update the manual editor."""
        # Read main pywal colors file
        wal_colors_file = paths.WAL_CACHE / "colors"
        if not wal_colors_file.exists():
            show_toast(self, "No pywal colors found", timeout=4)
            return
        
        # Parse hex colors (without # prefix for swaylock)
        hex_colors = []
        try:
            for line in wal_colors_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("#") and len(line) == 7:
                    hex_colors.append(line[1:].upper())
        except OSError:
            show_toast(self, "Failed to read pywal colors", timeout=4)
            return
        
        if len(hex_colors) < 8:
            show_toast(self, "Pywal colors file incomplete", timeout=4)
            return
        
        # Map pywal colors to swaylock keys
        # color0=black, color1=red, color2=green, color3=yellow
        # color4=blue, color5=magenta, color6=cyan, color7=white
        wal_map = {
            "ring-color": hex_colors[6],           # cyan
            "ring-clear-color": hex_colors[4],     # blue
            "ring-wrong-color": hex_colors[1],     # red
            "ring-ver-color": hex_colors[5],       # magenta
            "ring-caps-lock-color": hex_colors[5], # magenta
            "inside-color": hex_colors[0],         # black
            "inside-clear-color": hex_colors[4],   # blue
            "inside-wrong-color": hex_colors[1],   # red
            "inside-ver-color": hex_colors[5],     # magenta
            "key-hl-color": hex_colors[6],         # cyan
            "text-color": hex_colors[7],           # white
            "bs-hl-color": hex_colors[1],          # red
        }
        
        preview_colors = {}
        for key, cb in self._color_buttons.items():
            val = wal_map.get(key, "#ffffff")
            cb.set_color(f"#{val}")
            preview_colors[key] = f"#{val}"
        self._preview.update_colors(preview_colors)
        self._preview.queue_draw()
        show_toast(self, "Loaded pywal colors")

    def _apply_pywal(self, btn):
        """Update swaylock config colors with current pywal colors."""
        # Read main pywal colors
        wal_colors_file = paths.WAL_CACHE / "colors"
        if not wal_colors_file.exists():
            show_toast(self, "No pywal colors found", timeout=4)
            return
        
        hex_colors = []
        try:
            for line in wal_colors_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("#") and len(line) == 7:
                    hex_colors.append(line[1:].upper())
        except OSError:
            show_toast(self, "Failed to read pywal colors", timeout=4)
            return
        
        if len(hex_colors) < 8:
            show_toast(self, "Pywal colors file incomplete", timeout=4)
            return
        
        # Map pywal color indices to swaylock color keys
        # Each tuple: (swaylock_key, pywal_index, keep_alpha)
        color_mapping = [
            ("ring-color", 6, False),
            ("ring-clear-color", 4, False),
            ("ring-wrong-color", 1, False),
            ("ring-ver-color", 5, False),
            ("ring-caps-lock-color", 5, False),
            ("inside-color", 0, True),
            ("inside-clear-color", 4, True),
            ("inside-wrong-color", 1, True),
            ("inside-ver-color", 5, True),
            ("inside-caps-lock-color", 5, True),
            ("key-hl-color", 6, True),
            ("text-color", 7, False),
            ("text-clear-color", 4, False),
            ("text-ver-color", 5, False),
            ("text-wrong-color", 1, False),
            ("bs-hl-color", 1, False),
            ("line-color", 6, True),
            ("line-clear-color", 4, True),
            ("line-wrong-color", 1, True),
            ("line-ver-color", 5, True),
            ("line-caps-lock-color", 5, True),
            ("caps-lock-key-hl-color", 5, True),
            ("caps-lock-bs-hl-color", 5, True),
            ("text-caps-lock-color", 5, False),
        ]
        
        # Build replacement dict
        replacements = {}
        for key, idx, keep_alpha in color_mapping:
            new_color = hex_colors[idx]
            if keep_alpha:
                # Use 44 alpha (27% opacity) for transparent elements
                replacements[key] = f"{new_color}44"
            else:
                replacements[key] = new_color
        
        # Read original config template
        template = paths.WAL_CACHE / "colors-swaylock.conf"
        if not template.exists():
            show_toast(self, "No swaylock template found", timeout=4)
            return
        
        # Update colors in-place, preserving structure and alpha
        lines = template.read_text().splitlines()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in replacements:
                    new_lines.append(f"{key}={replacements[key]}")
                    continue
            new_lines.append(line)
        
        # Save updated config
        paths.SWAYLOCK_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        paths.SWAYLOCK_CONFIG.write_text("\n".join(new_lines) + "\n")
        
        # Update UI
        self._load()
        show_toast(self, "Swaylock colors applied and saved")

    def _save_manual(self, btn):
        config = read_swaylock_config()
        for key, cb in self._color_buttons.items():
            config[key] = cb.get_color().lstrip("#")
        write_swaylock_config(config)
        show_toast(self, "Swaylock colors saved")

    def _save_settings(self, btn):
        config = read_swaylock_config()
        config["indicator-radius"] = self._indicator_radius.get_text()
        config["indicator-thickness"] = self._indicator_thickness.get_text()
        config["fade-in"] = self._fade_in.get_text()

        for key in list(config.keys()):
            if key.startswith("effect-"):
                del config[key]

        effect_text = self._effect.get_text().strip()
        if "=" in effect_text:
            k, _, v = effect_text.partition("=")
            config[k] = v

        write_swaylock_config(config)
        show_toast(self, "Swaylock settings saved")
