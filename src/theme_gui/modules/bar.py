"""hyprtk-bar theme manager with error handling and loading feedback."""
from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

from gi.repository import Adw, Gtk

from .. import paths
from ..widgets import BasePage, remove_all_children, show_toast

log = logging.getLogger(__name__)


class BarPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Bar Themes", **kwargs)
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
        launch_btn = Gtk.Button(label="Restart Bar")
        launch_btn.add_css_class("flat")
        launch_btn.connect("clicked", self._restart_bar)
        self._box.append(launch_btn)

        self._refresh()
        self.connect("map", lambda w: self._refresh())

    def _refresh(self):
        self._load_active()
        self._load_themes()

    def _load_active(self):
        self._active_theme = ""
        try:
            cfg = json.loads(paths.BAR_CONFIG.read_text())
        except (OSError, json.JSONDecodeError):
            self._active_label.set_text("Active theme: (none)")
            return

        theme = cfg.get("theme") or {}
        source = theme.get("source", "pywal")
        name = theme.get("waybar_theme") or ""
        if source == "waybar" and name:
            self._active_theme = Path(name).name
            self._active_label.set_text(f"Active theme: {self._active_theme}")
        else:
            self._active_theme = ""
            self._active_label.set_text("Active theme: (pywal / none)")

    def _load_themes(self):
        remove_all_children(self._theme_list)

        themes_dir = paths.BAR_THEMES
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

        try:
            cfg = json.loads(paths.BAR_CONFIG.read_text())
        except (OSError, json.JSONDecodeError):
            cfg = {}
        cfg.setdefault("theme", {})
        cfg["theme"]["source"] = "waybar"
        cfg["theme"]["waybar_theme"] = theme_name
        try:
            paths.BAR_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            paths.BAR_CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
        except OSError as exc:
            log.warning("Failed to write bar config: %s", exc)
            show_toast(self, "Failed to write bar config", timeout=4)
            return

        self._restart_bar(None)
        self._refresh()
        show_toast(self, f"Bar restarted with {theme_name}")

    def _restart_bar(self, btn):
        """Restart hyprtk-bar so the new theme is picked up.

        pkill must match the bar's invocation (``python3 -m hyprtk_bar``) and
        not the ``bash -c`` wrapper itself. The ``[h]yprtk_bar`` character
        class trick makes the pattern not match this wrapper's own command line
        (which contains the literal ``[h]yprtk_bar``), so pkill only kills the
        bar.
        """
        launcher = paths.BAR_LAUNCHER
        if not launcher.is_file():
            show_toast(self, "hyprtk-bar launcher not found", timeout=4)
            return
        try:
            subprocess.Popen(
                [
                    "bash", "-c",
                    f"pkill -f '[h]yprtk_bar'; "
                    f"sleep 0.5; setsid {launcher} &",
                ],
                start_new_session=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            log.warning("failed to restart bar: %s", exc)
            show_toast(self, "Failed to restart bar", timeout=4)