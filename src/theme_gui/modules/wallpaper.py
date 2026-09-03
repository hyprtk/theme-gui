"""Wallpaper browser with cached thumbnails and background loading."""
from __future__ import annotations

import logging
import os
import random
import subprocess
from pathlib import Path

from gi.repository import Adw, Gio, GLib, Gtk

from .. import paths
from ..cache import build_index, is_valid, load_index
from ..colors import hex_to_rgb
from ..widgets import BasePage, remove_all_children, show_toast

log = logging.getLogger(__name__)

_BATCH_SIZE = 20
POST_ACTION_DELAY_MS = 3000


class WallpaperPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Wallpaper", **kwargs)
        self._css_provider = None
        self._all_images: list[Path] = []
        self._thumb_map: dict[str, str] = {}
        self._loaded_count = 0

        # current wallpaper display
        self._current_img = Gtk.Picture()
        self._current_img.set_size_request(-1, 200)
        self._current_img.add_css_class("preview-frame")
        self._current_img.set_content_fit(Gtk.ContentFit.CONTAIN)
        self._box.append(self._current_img)

        # wallpaper directory chooser
        dir_row = Adw.ActionRow(title="Wallpaper Directory")
        self._dir_label = Gtk.Label(label=str(paths.WALLPAPER_DIRS[0]))
        self._dir_label.set_ellipsize(3)
        self._dir_label.set_tooltip_text(str(paths.WALLPAPER_DIRS[0]))
        dir_row.add_suffix(self._dir_label)
        dir_btn = Gtk.Button(label="Choose")
        dir_btn.add_css_class("flat")
        dir_btn.connect("clicked", self._choose_dir)
        dir_row.add_suffix(dir_btn)
        self._box.append(dir_row)

        # apply + random buttons
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_homogeneous(True)
        btn_row.set_hexpand(True)

        apply_btn = Gtk.Button(label="Apply Wallpaper")
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", self._apply_selected)
        btn_row.append(apply_btn)

        random_btn = Gtk.Button(label="Random")
        random_btn.add_css_class("flat")
        random_btn.add_css_class("random-btn")
        random_btn.connect("clicked", self._apply_random)
        btn_row.append(random_btn)
        self._box.append(btn_row)

        # loading spinner
        self._spinner = Gtk.Spinner()
        self._box.append(self._spinner)

        # thumbnail flow box
        self._flow = Gtk.FlowBox()
        self._flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._flow.set_column_spacing(8)
        self._flow.set_row_spacing(8)
        self._flow.set_homogeneous(True)
        self._flow.set_min_children_per_line(2)
        self._flow.set_max_children_per_line(6)
        self._flow.set_vexpand(True)

        self._box.append(self._flow)
        self._scroll.connect("edge-reached", self._on_scroll_edge)

        self._wallpaper_dir = Path(str(paths.WALLPAPER_DIRS[0]))
        self._selected_path: Path | None = None
        self._load_current()
        self._load_thumbnails()
        self.connect("map", lambda w: self._refresh())

    def _refresh(self):
        self._load_current()
        self._load_thumbnails()

    def _load_current(self):
        wal_file = paths.WAL_CACHE / "wal"
        if wal_file.exists():
            wp = wal_file.read_text().strip()
            if wp and os.path.isfile(wp):
                self._current_img.set_filename(wp)
                return
        fallback = paths.HYPRTK / "assets" / "Wallpapers" / "default.png"
        if fallback.exists():
            self._current_img.set_filename(str(fallback))

    def _load_thumbnails(self):
        remove_all_children(self._flow)
        self._loaded_count = 0

        if not self._wallpaper_dir.exists():
            return

        # build or load cache (from disk, not main thread blocking)
        if not is_valid(self._wallpaper_dir):
            self._spinner.set_visible(True)
            self._spinner.start()
            # use idle to avoid blocking initial render
            GLib.idle_add(self._build_cache_idle)
        else:
            index = load_index()
            self._set_index(index)

    def _build_cache_idle(self):
        """Build cache in idle callback to avoid blocking UI."""
        try:
            index = build_index(self._wallpaper_dir)
            self._set_index(index)
        except Exception as exc:
            log.warning("cache build failed: %s", exc)
        finally:
            self._spinner.stop()
            self._spinner.set_visible(False)
        return False  # don't repeat

    def _set_index(self, index: list[dict]):
        self._all_images = [Path(e["path"]) for e in index]
        self._thumb_map = {e["path"]: e["thumb"] for e in index}
        self._load_batch()

    def _load_batch(self):
        """Load next _BATCH_SIZE thumbnails into the flow box."""
        start = self._loaded_count
        end = min(start + _BATCH_SIZE, len(self._all_images))
        for img_path in self._all_images[start:end]:
            btn = Gtk.Button()
            btn.add_css_class("flat")
            btn.set_size_request(160, 120)

            pic = Gtk.Picture()
            thumb = self._thumb_map.get(str(img_path))
            if thumb and os.path.isfile(thumb):
                pic.set_filename(thumb)
            else:
                pic.set_filename(str(img_path))
            pic.set_size_request(150, 100)
            pic.set_content_fit(Gtk.ContentFit.COVER)
            btn.set_child(pic)

            btn.connect("clicked", self._on_thumb_click, img_path)
            self._flow.append(btn)
        self._loaded_count = end

    def _on_scroll_edge(self, scroll, pos):
        if pos == Gtk.PositionType.BOTTOM and self._loaded_count < len(self._all_images):
            self._load_batch()

    def _on_thumb_click(self, btn, path: Path):
        self._selected_path = path
        self._current_img.set_filename(str(path))

    def _apply_random(self, btn):
        if not self._all_images:
            return
        path = random.choice(self._all_images)
        self._selected_path = path
        self._current_img.set_filename(str(path))
        self._apply_selected(btn)

    def _choose_dir(self, btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Wallpaper Directory")
        folder = Gio.File.new_for_path(str(self._wallpaper_dir))
        dialog.set_initial_folder(folder)
        dialog.select_folder(self.get_root(), None, self._on_dir_chosen)

    def _on_dir_chosen(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self._wallpaper_dir = Path(folder.get_path())
                self._dir_label.set_text(str(self._wallpaper_dir))
                self._dir_label.set_tooltip_text(str(self._wallpaper_dir))
                build_index(self._wallpaper_dir, force=True)
                self._load_thumbnails()
        except GLib.Error:
            pass

    def _apply_selected(self, btn):
        if not self._selected_path:
            return
        script = str(paths.WALLPAPER_COLORS_SH)
        if not Path(script).is_file():
            show_toast(self, "Wallpaper script not found", timeout=4)
            return
        try:
            subprocess.Popen(
                ["bash", script, str(self._selected_path)],
                start_new_session=True,
            )
            show_toast(self, f"Applied: {self._selected_path.name}")
        except FileNotFoundError:
            show_toast(self, "Failed to run wallpaper script", timeout=4)
            return
        GLib.timeout_add(POST_ACTION_DELAY_MS, self._refresh_app_css)

    def _refresh_app_css(self):
        from ..app import build_app_css
        from gi.repository import Gdk

        if self._css_provider is None:
            self._css_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                self._css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
            )
        try:
            self._css_provider.load_from_data(build_app_css().encode())
        except GLib.Error as exc:
            log.warning("failed to reload app css: %s", exc)
        return False
