"""Pywal color palette viewer and manager."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from gi.repository import Adw, Gio, GLib, Gtk

from .. import paths
from ..colors import get_color_name, parse_wal_colors
from ..widgets import BasePage, remove_all_children, show_toast
from ..widgets.color_grid import ColorGrid

log = logging.getLogger(__name__)

MAX_SCHEMES = 30
POST_ACTION_DELAY_MS = 2000


class PywalPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Pywal Colors", **kwargs)

        # section title
        title = Gtk.Label(label="Current Pywal Palette")
        title.add_css_class("heading")
        title.set_xalign(0)
        self._box.append(title)

        # color grid
        self._grid = ColorGrid()
        self._grid.connect_color_selected(self._on_color_selected)
        self._box.append(self._grid)

        # selected color detail
        self._detail_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._detail_label = Gtk.Label(label="Click a color to inspect")
        self._detail_label.set_xalign(0)
        self._detail_box.append(self._detail_label)
        self._box.append(self._detail_box)

        # color scheme section
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self._box.append(sep)

        scheme_label = Gtk.Label(label="Colorscheme Files")
        scheme_label.add_css_class("heading")
        scheme_label.set_xalign(0)
        self._box.append(scheme_label)

        self._scheme_list = Gtk.ListBox()
        self._scheme_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.append(self._scheme_list)

        # re-run wal button
        rerun_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._wal_dir_label = Gtk.Label(label=str(paths.WALLPAPER_DIRS[0]))
        self._wal_dir_label.set_ellipsize(3)
        self._wal_dir_label.set_tooltip_text(str(paths.WALLPAPER_DIRS[0]))
        rerun_box.append(self._wal_dir_label)

        choose_dir_btn = Gtk.Button(label="Dir")
        choose_dir_btn.add_css_class("flat")
        choose_dir_btn.connect("clicked", self._choose_wal_dir)
        rerun_box.append(choose_dir_btn)

        rerun_btn = Gtk.Button(label="Re-run wal")
        rerun_btn.add_css_class("suggested-action")
        rerun_btn.connect("clicked", self._rerun_wal)
        rerun_box.append(rerun_btn)

        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.add_css_class("flat")
        refresh_btn.connect("clicked", lambda b: self._refresh())
        rerun_box.append(refresh_btn)
        self._box.append(rerun_box)

        self._wal_dir = Path(str(paths.WALLPAPER_DIRS[0]))
        self.connect("map", lambda w: self._refresh())

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
            row = Adw.ActionRow(title=f.name)
            row.set_activatable(True)
            row.add_css_class("sidebar-row")
            row._scheme_path = f
            row.connect("activated", self._on_scheme_click)
            self._scheme_list.append(row)

    def _on_scheme_click(self, row):
        try:
            subprocess.Popen(
                ["wal", "--theme", str(row._scheme_path)],
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
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Wallpaper Directory for wal")
        folder = Gio.File.new_for_path(str(self._wal_dir))
        dialog.set_initial_folder(folder)
        dialog.select_folder(self.get_root(), None, self._on_dir_chosen)

    def _on_dir_chosen(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self._wal_dir = Path(folder.get_path())
                self._wal_dir_label.set_text(str(self._wal_dir))
                self._wal_dir_label.set_tooltip_text(str(self._wal_dir))
        except GLib.Error:
            pass

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
