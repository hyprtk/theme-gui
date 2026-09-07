"""Swaylock theme editor with live preview (GTK3)."""
from __future__ import annotations

import shutil
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import Gtk, Pango  # noqa: E402

from .. import paths  # noqa: E402
from ..colors import (
    hex_to_rgb_float,
    read_swaylock_config,
    write_swaylock_config,
)  # noqa: E402
from ..widgets import BasePage, show_toast  # noqa: E402
from ..widgets.color_button import ColorButton  # noqa: E402


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
        self.connect("draw", self._draw)

    def update_colors(self, colors: dict[str, str]):
        self._colors.update(colors)
        self.queue_draw()

    def set_dimensions(self, radius: int, thickness: int):
        self._indicator_radius = radius
        self._indicator_thickness = thickness
        self.queue_draw()

    def _draw(self, _widget, cr):
        import cairo

        width = self.get_allocated_width()
        height = self.get_allocated_height()
        cx, cy = width / 2, height / 2
        radius = min(self._indicator_radius, min(width, height) / 2 - 8)

        r, g, b = hex_to_rgb_float(self._colors.get("ring-color", "#ffffff"))
        cr.set_source_rgb(r, g, b)
        cr.arc(cx, cy, radius, 0, 2 * 3.14159)
        cr.set_line_width(self._indicator_thickness * 0.9)
        cr.stroke()

        r, g, b = hex_to_rgb_float(self._colors.get("inside-color", "#000000"))
        cr.set_source_rgb(r, g, b)
        cr.arc(cx, cy, radius * 0.72, 0, 2 * 3.14159)
        cr.fill()

        r, g, b = hex_to_rgb_float(self._colors.get("key-hl-color", "#22d3ee"))
        cr.set_source_rgb(r, g, b)
        dot_r = radius * 0.08
        cr.arc(cx, cy - radius * 0.91, dot_r, 0, 2 * 3.14159)
        cr.fill()

        r, g, b = hex_to_rgb_float(self._colors.get("bs-hl-color", "#ff0000"))
        cr.set_source_rgb(r, g, b)
        cr.arc(cx, cy + radius * 0.91, dot_r, 0, 2 * 3.14159)
        cr.fill()

        r, g, b = hex_to_rgb_float(self._colors.get("text-color", "#ffffff"))
        cr.set_source_rgb(r, g, b)
        cr.select_font_face(
            "sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD
        )
        cr.set_font_size(radius * 0.35)
        ext = cr.text_extents("Password")
        cr.move_to(cx - ext.width / 2, cy + ext.height / 3)
        cr.show_text("Password")
        return False


class SwaylockPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Swaylock", **kwargs)

        # pywal mode
        wal_sec = self.section("Pywal Mode")
        wal_desc = Gtk.Label(
            label="Copy pywal-generated colors to swaylock config. This syncs "
            "the lock screen with your current wallpaper palette.",
            xalign=0,
            wrap=True,
        )
        wal_desc.get_style_context().add_class("dim-label")
        wal_sec.pack_start(wal_desc, False, False, 0)
        apply_wal_btn = self.primary_button("Apply Pywal Colors")
        apply_wal_btn.connect("clicked", self._apply_pywal)
        wal_sec.pack_start(apply_wal_btn, False, False, 0)

        # manual color editor
        manual_sec = self.section("Manual Color Editor")
        refresh_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        load_pywal_btn = self.flat_button("Load Current Pywal Colors")
        load_pywal_btn.connect("clicked", self._load_pywal_colors)
        refresh_box.pack_start(load_pywal_btn, False, False, 0)
        manual_sec.pack_start(refresh_box, False, False, 0)

        self._color_buttons: dict[str, ColorButton] = {}
        manual_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self._preview = SwaylockPreview()
        self._preview.set_valign(Gtk.Align.START)
        manual_row.pack_start(self._preview, False, False, 0)

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
            grid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            grid.set_valign(Gtk.Align.START)
            for key, label_text in group:
                r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                lbl = Gtk.Label(label=label_text, xalign=0)
                lbl.set_size_request(140, -1)
                r.pack_start(lbl, False, False, 0)
                cb = ColorButton()
                cb.connect_color_changed(
                    lambda btn, hex_val, k=key: self._on_color_change(k, hex_val)
                )
                self._color_buttons[key] = cb
                r.pack_start(cb, False, False, 0)
                grid.pack_start(r, False, False, 0)
            manual_row.pack_start(grid, False, False, 0)
        manual_sec.pack_start(manual_row, False, False, 0)

        save_btn = self.primary_button("Save Manual Config")
        save_btn.connect("clicked", self._save_manual)
        manual_sec.pack_start(save_btn, False, False, 0)

        # indicator settings
        settings_sec = self.section("Indicator Settings")
        self._indicator_radius = self._entry_row(settings_sec, "Indicator Radius")
        self._indicator_thickness = self._entry_row(
            settings_sec, "Indicator Thickness"
        )
        self._fade_in = self._entry_row(settings_sec, "Fade-in (seconds)")
        self._effect = self._entry_row(
            settings_sec, "Effect (e.g. effect-pixelate=5)"
        )
        save_settings_btn = self.primary_button("Save Settings")
        save_settings_btn.connect("clicked", self._save_settings)
        settings_sec.pack_start(save_settings_btn, False, False, 0)

        self._load()

    def on_shown(self):
        self._load()

    @staticmethod
    def _entry_row(parent, title: str) -> Gtk.Entry:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.set_size_request(160, -1)
        row.pack_start(lbl, False, False, 0)
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        row.pack_start(entry, True, True, 0)
        parent.pack_start(row, False, False, 0)
        return entry

    def _load(self):
        config = read_swaylock_config()
        wal_colors_file = paths.WAL_CACHE / "colors"
        if wal_colors_file.exists():
            try:
                hex_colors = [
                    line[1:].upper()
                    for line in wal_colors_file.read_text().splitlines()
                    if line.strip().startswith("#") and len(line.strip()) == 7
                ]
                if len(hex_colors) >= 8:
                    wal_map = {
                        "ring-color": hex_colors[6],
                        "ring-clear-color": hex_colors[4],
                        "ring-wrong-color": hex_colors[1],
                        "ring-ver-color": hex_colors[5],
                        "ring-caps-lock-color": hex_colors[5],
                        "inside-color": hex_colors[0],
                        "inside-clear-color": hex_colors[4],
                        "inside-wrong-color": hex_colors[1],
                        "inside-ver-color": hex_colors[5],
                        "key-hl-color": hex_colors[6],
                        "text-color": hex_colors[7],
                        "bs-hl-color": hex_colors[1],
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
        wal_colors_file = paths.WAL_CACHE / "colors"
        if not wal_colors_file.exists():
            show_toast(self, "No pywal colors found", timeout=4)
            return
        try:
            hex_colors = [
                line[1:].upper()
                for line in wal_colors_file.read_text().splitlines()
                if line.strip().startswith("#") and len(line.strip()) == 7
            ]
        except OSError:
            show_toast(self, "Failed to read pywal colors", timeout=4)
            return
        if len(hex_colors) < 8:
            show_toast(self, "Pywal colors file incomplete", timeout=4)
            return
        wal_map = {
            "ring-color": hex_colors[6],
            "ring-clear-color": hex_colors[4],
            "ring-wrong-color": hex_colors[1],
            "ring-ver-color": hex_colors[5],
            "ring-caps-lock-color": hex_colors[5],
            "inside-color": hex_colors[0],
            "inside-clear-color": hex_colors[4],
            "inside-wrong-color": hex_colors[1],
            "inside-ver-color": hex_colors[5],
            "key-hl-color": hex_colors[6],
            "text-color": hex_colors[7],
            "bs-hl-color": hex_colors[1],
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
        wal_colors_file = paths.WAL_CACHE / "colors"
        if not wal_colors_file.exists():
            show_toast(self, "No pywal colors found", timeout=4)
            return
        try:
            hex_colors = [
                line[1:].upper()
                for line in wal_colors_file.read_text().splitlines()
                if line.strip().startswith("#") and len(line.strip()) == 7
            ]
        except OSError:
            show_toast(self, "Failed to read pywal colors", timeout=4)
            return
        if len(hex_colors) < 8:
            show_toast(self, "Pywal colors file incomplete", timeout=4)
            return

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
        replacements = {}
        for key, idx, keep_alpha in color_mapping:
            new_color = hex_colors[idx]
            replacements[key] = f"{new_color}44" if keep_alpha else new_color

        template = paths.WAL_CACHE / "colors-swaylock.conf"
        if not template.exists():
            show_toast(self, "No swaylock template found", timeout=4)
            return

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

        paths.SWAYLOCK_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        paths.SWAYLOCK_CONFIG.write_text("\n".join(new_lines) + "\n")

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
