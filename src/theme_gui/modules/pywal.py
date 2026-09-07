"""Pywal color palette viewer and manager (GTK3)."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import GLib, Gtk, Pango  # noqa: E402

from .. import paths  # noqa: E402
from ..colors import get_color_name, parse_wal_colors  # noqa: E402
from ..widgets import BasePage, remove_all_children, show_toast  # noqa: E402
from ..widgets.color_grid import ColorGrid  # noqa: E402

log = logging.getLogger(__name__)

MAX_SCHEMES = 30
POST_ACTION_DELAY_MS = 2000


class PywalPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Pywal Colors", **kwargs)
        self._wal_dir = Path(str(paths.WALLPAPER_DIRS[0]))

        palette_sec = self.section("Current Pywal Palette")
        self._grid = ColorGrid()
        self._grid.connect_color_selected(self._on_color_selected)
        palette_sec.pack_start(self._grid, False, False, 0)

        self._detail_label = Gtk.Label(label="Click a color to inspect", xalign=0)
        self._detail_label.get_style_context().add_class("dim-label")
        palette_sec.pack_start(self._detail_label, False, False, 0)

        schemes_sec = self.section("Colorscheme Files")
        self._scheme_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        schemes_sec.pack_start(self._scheme_list, False, False, 0)

        # re-run wal controls
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._wal_dir_label = Gtk.Label(label=str(self._wal_dir), xalign=0)
        self._wal_dir_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._wal_dir_label.set_hexpand(True)
        actions.pack_start(self._wal_dir_label, True, True, 0)

        dir_btn = self.flat_button("Dir")
        dir_btn.connect("clicked", self._choose_wal_dir)
        actions.pack_start(dir_btn, False, False, 0)
        rerun_btn = self.primary_button("Re-run wal")
        rerun_btn.connect("clicked", self._rerun_wal)
        actions.pack_start(rerun_btn, False, False, 0)
        refresh_btn = self.flat_button("Refresh")
        refresh_btn.connect("clicked", lambda b: self._refresh())
        actions.pack_start(refresh_btn, False, False, 0)
        self.body.pack_start(actions, False, False, 0)

        self._refresh()

    def on_shown(self):
        self._refresh()

    def _refresh(self):
        colors = parse_wal_colors()
        if colors:
            self._grid.set_colors(colors)
        self._load_schemes()

    def _load_schemes(self):
        remove_all_children(self._scheme_list)
        schemes_dir = paths.WAL_CACHE / "schemes"
        if not schemes_dir.exists():
            return
        for f in sorted(schemes_dir.iterdir())[:MAX_SCHEMES]:
            row = Gtk.Button()
            row.get_style_context().add_class("flat")
            row.get_style_context().add_class("tg-row")
            row.set_halign(Gtk.Align.FILL)
            lbl = Gtk.Label(label=f.name, xalign=0)
            row.add(lbl)
            row.connect("clicked", self._on_scheme_click, f)
            self._scheme_list.pack_start(row, False, False, 0)
        self._scheme_list.show_all()

    def _on_scheme_click(self, _btn, scheme_path: Path):
        try:
            subprocess.Popen(
                ["wal", "--theme", str(scheme_path)],
                start_new_session=True,
            )
            GLib.timeout_add(POST_ACTION_DELAY_MS, self._do_refresh)
        except FileNotFoundError:
            show_toast(self, "wal command not found", timeout=4)

    def _on_color_selected(self, index: int, key: str):
        colors = parse_wal_colors()
        val = colors.get(key, "N/A")
        name = get_color_name(index)
        self._detail_label.set_text(f"{name} ({key}): {val}")

    def _choose_wal_dir(self, btn):
        chooser = Gtk.FileChooserNative.new(
            "Select Wallpaper Directory for wal",
            self.get_toplevel(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            "Select",
            "Cancel",
        )
        chooser.set_current_folder(str(self._wal_dir))

        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                folder = dialog.get_filename()
                if folder:
                    self._wal_dir = Path(folder)
                    self._wal_dir_label.set_text(str(self._wal_dir))
                    self._wal_dir_label.set_tooltip_text(str(self._wal_dir))
            dialog.destroy()

        chooser.connect("response", on_response)
        chooser.show()

    def _rerun_wal(self, btn):
        try:
            subprocess.Popen(
                ["wal", "-i", str(self._wal_dir)],
                start_new_session=True,
            )
            GLib.timeout_add(POST_ACTION_DELAY_MS, self._do_refresh)
        except FileNotFoundError:
            show_toast(self, "wal command not found", timeout=4)

    def _do_refresh(self):
        self._refresh()
        return False
