"""Waybar theme manager with error handling and loading feedback."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from gi.repository import Adw, Gtk

from .. import paths
from ..widgets import BasePage, remove_all_children, show_toast

log = logging.getLogger(__name__)


class WaybarPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Waybar Themes", **kwargs)
        self._active_theme = ""

        # active theme indicator
        self._active_label = Gtk.Label(label="Active theme: ...")
        self._active_label.set_xalign(0)
        self._active_label.add_css_class("heading")
        self._box.append(self._active_label)

        # theme list
        self._theme_list = Gtk.ListBox()
        self._theme_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.append(self._theme_list)

        # manual refresh button
        launch_btn = Gtk.Button(label="Refresh Waybar")
        launch_btn.add_css_class("flat")
        launch_btn.connect("clicked", self._launch_waybar)
        self._box.append(launch_btn)

        self._refresh()
        self.connect("map", lambda w: self._refresh())

    def _refresh(self):
        self._load_active()
        self._load_themes()

    def _load_active(self):
        cache = paths.THEME_STYLE_CACHE
        self._active_theme = ""
        try:
            if cache.exists():
                content = cache.read_text().strip()
                if ";" in content:
                    parts = content.split(";")
                    self._active_theme = Path(parts[0]).name
                elif content:
                    self._active_theme = Path(content).name
                self._active_label.set_text(f"Active theme: {self._active_theme}")
            else:
                self._active_label.set_text("Active theme: (none)")
        except (OSError, ValueError):
            self._active_label.set_text("Active theme: (error)")

    def _load_themes(self):
        remove_all_children(self._theme_list)

        themes_dir = paths.WAYBAR_THEMES
        if not themes_dir.exists():
            return

        for d in sorted(themes_dir.iterdir()):
            if not d.is_dir():
                continue
            if not (d / "style.css").exists():
                continue

            name = d.name
            display_name = name
            config_sh = d / "config.sh"
            if config_sh.exists():
                for line in config_sh.read_text().splitlines():
                    if "theme_name" in line and "=" in line:
                        display_name = line.split("=", 1)[1].strip().strip("'\"")
                        break

            row = Adw.ActionRow(title=display_name)
            if display_name != name and not (display_name.lower() == name):
                row.set_subtitle(name)
            row.set_activatable(True)
            row.add_css_class("sidebar-row")
            row._theme_dir = d

            if name == self._active_theme:
                badge = Gtk.Label(label="Active")
                badge.add_css_class("success")
                row.add_suffix(badge)

            row.connect("activated", self._on_theme_click)
            self._theme_list.append(row)

    def _on_theme_click(self, row):
        theme_dir = row._theme_dir
        theme_name = theme_dir.name

        cache = paths.THEME_STYLE_CACHE
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(f"/{theme_name};/{theme_name}")
        except OSError as exc:
            log.warning("Failed to write theme cache: %s", exc)

        # sync rofi
        self._run_script(paths.SYNC_ROFI_SH, "rofi sync")

        # restart waybar
        self._run_script(paths.WAYBAR_LAUNCH_SH, "waybar launch")

        self._refresh()
        show_toast(self, f"Waybar restarted with {theme_name}")

    def _launch_waybar(self, btn):
        self._run_script(paths.WAYBAR_LAUNCH_SH, "waybar launch")

    def _run_script(self, script_path, label: str):
        if not script_path.is_file():
            show_toast(self, f"{label} script not found", timeout=4)
            return
        try:
            subprocess.Popen(["bash", str(script_path)], start_new_session=True)
        except FileNotFoundError as exc:
            log.warning("%s failed: %s", label, exc)
            show_toast(self, f"Failed to run {label}", timeout=4)
