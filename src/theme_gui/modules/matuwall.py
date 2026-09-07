"""Matuwall wallpaper picker configuration (GTK3)."""
from __future__ import annotations

import json

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import Gtk, Pango  # noqa: E402

from .. import paths  # noqa: E402
from ..colors import _atomic_write  # noqa: E402
from ..widgets import BasePage, show_toast  # noqa: E402


class MatuwallPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Matuwall", **kwargs)
        self._config: dict = {}
        self._entries: dict[str, Gtk.Entry] = {}
        self._switches: dict[str, Gtk.Switch] = {}

        main_sec = self.section("Main")
        self._add_entry(main_sec, "wallpaper_dir", "Wallpaper Directory")
        self._add_entry(main_sec, "thumbnail_size", "Thumbnail Size")
        self._add_entry(main_sec, "batch_size", "Batch Size")
        self._add_switch(main_sec, "mouse_enabled", "Mouse Enabled")
        self._add_switch(main_sec, "keep_ui_alive", "Keep UI Alive")

        wall_sec = self.section("Wall Mode")
        self._add_switch(wall_sec, "wall_mode_only", "Wall Mode Only")
        self._add_entry(wall_sec, "wall_awww_flags", "Awww Transition Flags")

        panel_sec = self.section("Panel Mode")
        self._add_switch(panel_sec, "panel_mode", "Panel Mode")
        self._add_entry(panel_sec, "panel_edge", "Panel Edge")
        self._add_entry(panel_sec, "panel_exclusive_zone", "Exclusive Zone")

        save_btn = self.primary_button("Save Configuration")
        save_btn.connect("clicked", self._save)
        self.body.pack_start(save_btn, False, False, 0)

        self._load()

    def on_shown(self):
        self._load()

    def _add_entry(self, parent, key: str, title: str):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.set_size_request(160, -1)
        row.pack_start(lbl, False, False, 0)
        entry = Gtk.Entry()
        entry.set_hexpand(True)
        row.pack_start(entry, True, True, 0)
        self._entries[key] = entry
        parent.pack_start(row, False, False, 0)

    def _add_switch(self, parent, key: str, title: str):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.set_hexpand(True)
        row.pack_start(lbl, True, True, 0)
        switch = Gtk.Switch()
        row.pack_start(switch, False, False, 0)
        self._switches[key] = switch
        parent.pack_start(row, False, False, 0)

    def _load(self):
        if not paths.MATUWALL_CONFIG.exists():
            return
        try:
            self._config = json.loads(paths.MATUWALL_CONFIG.read_text())
        except (json.JSONDecodeError, OSError):
            return
        for section in self._config.values():
            if not isinstance(section, dict):
                continue
            for key, val in section.items():
                if key in self._entries:
                    self._entries[key].set_text(str(val))
                if key in self._switches:
                    self._switches[key].set_active(bool(val))

    def _save(self, btn):
        for key, entry in self._entries.items():
            val = entry.get_text()
            for section in self._config.values():
                if isinstance(section, dict) and key in section:
                    orig = section[key]
                    if isinstance(orig, int):
                        try:
                            section[key] = int(val)
                        except ValueError:
                            pass
                    elif isinstance(orig, float):
                        try:
                            section[key] = float(val)
                        except ValueError:
                            pass
                    elif isinstance(orig, bool):
                        pass
                    else:
                        section[key] = val
        for key, switch in self._switches.items():
            val = switch.get_active()
            for section in self._config.values():
                if isinstance(section, dict) and key in section:
                    section[key] = val
        try:
            _atomic_write(paths.MATUWALL_CONFIG, json.dumps(self._config, indent=2))
            show_toast(self, "Matuwall config saved")
        except OSError as e:
            show_toast(self, f"Save failed: {e}", timeout=4)
