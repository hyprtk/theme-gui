"""hyprtk-bar theme manager (GTK3)."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import GLib, Gtk, Pango  # noqa: E402

from .. import paths  # noqa: E402
from ..widgets import BasePage, remove_all_children, show_toast  # noqa: E402

log = logging.getLogger(__name__)


class BarPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Bar Themes", **kwargs)
        self._active_theme = ""

        self._active_label = Gtk.Label(label="Active theme: ...", xalign=0)
        self._active_label.get_style_context().add_class("heading")
        self.body.pack_start(self._active_label, False, False, 0)

        list_sec = self.section("Imported Themes")
        self._theme_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        list_sec.pack_start(self._theme_list, False, False, 0)

        launch_btn = self.flat_button("Restart Bar")
        launch_btn.connect("clicked", self._restart_bar)
        self.body.pack_start(launch_btn, False, False, 0)

        self._refresh()

    def on_shown(self):
        self._refresh()

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
        name = theme.get("theme_name") or ""
        if source == "imported" and name:
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
            if not d.is_dir() or not (d / "style.css").exists():
                continue
            name = d.name
            display_name = name
            config_sh = d / "config.sh"
            if config_sh.exists():
                for line in config_sh.read_text().splitlines():
                    if "theme_name" in line and "=" in line:
                        display_name = (
                            line.split("=", 1)[1].strip().strip("'\"")
                        )
                        break

            row = Gtk.Button()
            row.get_style_context().add_class("flat")
            row.get_style_context().add_class("tg-row")
            row.set_halign(Gtk.Align.FILL)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=display_name, xalign=0)
            lbl.set_hexpand(True)
            box.pack_start(lbl, True, True, 0)
            if display_name != name and not (display_name.lower() == name):
                sub = Gtk.Label(label=name, xalign=0)
                sub.get_style_context().add_class("dim-label")
                box.pack_start(sub, False, False, 0)
            if name == self._active_theme:
                badge = Gtk.Label(label="Active")
                badge.get_style_context().add_class("badge")
                box.pack_start(badge, False, False, 0)
                row.get_style_context().add_class("active")
            row.add(box)
            row.connect("clicked", self._on_theme_click, d)
            self._theme_list.pack_start(row, False, False, 0)
        self._theme_list.show_all()

    def _on_theme_click(self, _btn, theme_dir: Path):
        theme_name = theme_dir.name
        try:
            cfg = json.loads(paths.BAR_CONFIG.read_text())
        except (OSError, json.JSONDecodeError):
            cfg = {}
        cfg.setdefault("theme", {})
        cfg["theme"]["source"] = "imported"
        cfg["theme"]["theme_name"] = theme_name
        try:
            paths.BAR_CONFIG.parent.mkdir(parents=True, exist_ok=True)
            paths.BAR_CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
        except OSError as exc:
            log.warning("Failed to write bar config: %s", exc)
            show_toast(self, "Failed to write bar config", timeout=4)
            return

        self._restart_bar(None)
        self._refresh()
        GLib.timeout_add(800, self._refresh_app_css)
        show_toast(self, f"Bar restarted with {theme_name}")

    def _refresh_app_css(self):
        from ..theme import refresh_app_css

        refresh_app_css()
        return False

    def _restart_bar(self, btn):
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
