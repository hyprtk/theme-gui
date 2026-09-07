"""Wallpaper browser with cached thumbnails and background loading (GTK3)."""
from __future__ import annotations

import logging
import os
import random
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import GdkPixbuf, GLib, Gtk, Pango  # noqa: E402

from .. import paths  # noqa: E402
from ..cache import build_index, is_valid, load_index  # noqa: E402
from ..widgets import BasePage, remove_all_children, show_toast  # noqa: E402

log = logging.getLogger(__name__)

_BATCH_SIZE = 20
POST_ACTION_DELAY_MS = 3000


class WallpaperPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Wallpaper", **kwargs)
        self._all_images: list[Path] = []
        self._thumb_map: dict[str, str] = {}
        self._loaded_count = 0
        self._selected_path: Path | None = None
        self._wallpaper_dir = Path(str(paths.WALLPAPER_DIRS[0]))

        # current wallpaper preview
        preview = self.section("Current Wallpaper")
        self._current_img = Gtk.Image()
        self._current_img.set_size_request(-1, 180)
        self._current_img.get_style_context().add_class("preview-frame")
        self._current_img.set_halign(Gtk.Align.FILL)
        preview.pack_start(self._current_img, False, False, 0)

        # wallpaper directory chooser
        dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._dir_label = Gtk.Label(label=str(self._wallpaper_dir), xalign=0)
        self._dir_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._dir_label.set_tooltip_text(str(self._wallpaper_dir))
        self._dir_label.set_hexpand(True)
        dir_box.pack_start(self._dir_label, True, True, 0)
        dir_btn = self.flat_button("Choose")
        dir_btn.connect("clicked", self._choose_dir)
        dir_box.pack_start(dir_btn, False, False, 0)
        preview.pack_start(dir_box, False, False, 0)

        # apply + random buttons
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        apply_btn = self.primary_button("Apply Wallpaper")
        apply_btn.connect("clicked", self._apply_selected)
        btn_row.pack_start(apply_btn, True, True, 0)
        random_btn = self.flat_button("Random")
        random_btn.connect("clicked", self._apply_random)
        btn_row.pack_start(random_btn, False, False, 0)
        preview.pack_start(btn_row, False, False, 0)

        # thumbnail grid
        grid_sec = self.section("Wallpapers")
        self._spinner = Gtk.Spinner()
        self._spinner.get_style_context().add_class("loading-spinner")
        grid_sec.pack_start(self._spinner, False, False, 0)

        self._flow = Gtk.FlowBox()
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_column_spacing(8)
        self._flow.set_row_spacing(8)
        self._flow.set_homogeneous(True)
        self._flow.set_min_children_per_line(2)
        self._flow.set_max_children_per_line(6)
        self._flow.set_vexpand(True)
        grid_sec.pack_start(self._flow, True, True, 0)

        self._load_current()
        self._load_thumbnails()

    def on_shown(self):
        self._load_current()
        self._load_thumbnails()

    # ── loading ───────────────────────────────────────────────

    def _load_current(self):
        wp = ""
        wal_file = paths.WAL_CACHE / "wal"
        if wal_file.exists():
            wp = wal_file.read_text().strip()
        if not wp or not os.path.isfile(wp):
            fallback = paths.HYPRTK / "assets" / "Wallpapers" / "default.png"
            if fallback.exists():
                wp = str(fallback)
            else:
                return
        self._set_image(self._current_img, wp, -1, 180)

    @staticmethod
    def _set_image(img: Gtk.Image, path: str, width: int, height: int):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                path, width, height, True
            )
            img.set_from_pixbuf(pixbuf)
        except Exception as exc:
            log.warning("failed to load image %s: %s", path, exc)

    def _load_thumbnails(self):
        remove_all_children(self._flow)
        self._loaded_count = 0
        if not self._wallpaper_dir.exists():
            return
        if not is_valid(self._wallpaper_dir):
            self._spinner.set_visible(True)
            self._spinner.start()
            GLib.idle_add(self._build_cache_idle)
        else:
            index = load_index()
            self._set_index(index)

    def _build_cache_idle(self):
        try:
            index = build_index(self._wallpaper_dir)
            self._set_index(index)
        except Exception as exc:
            log.warning("cache build failed: %s", exc)
        finally:
            self._spinner.stop()
            self._spinner.set_visible(False)
        return False

    def _set_index(self, index: list[dict]):
        self._all_images = [Path(e["path"]) for e in index]
        self._thumb_map = {e["path"]: e["thumb"] for e in index}
        self._load_batch()

    def _load_batch(self):
        start = self._loaded_count
        end = min(start + _BATCH_SIZE, len(self._all_images))
        for img_path in self._all_images[start:end]:
            btn = Gtk.Button()
            btn.get_style_context().add_class("flat")
            btn.get_style_context().add_class("thumb-tile")
            btn.set_size_request(150, 100)

            thumb = self._thumb_map.get(str(img_path))
            pic_path = thumb if thumb and os.path.isfile(thumb) else str(img_path)
            img = Gtk.Image()
            self._set_image(img, pic_path, 150, 100)
            btn.add(img)
            btn.connect("clicked", self._on_thumb_click, img_path)
            self._flow.add(btn)
        self._loaded_count = end
        self._flow.show_all()

    def _on_thumb_click(self, btn, path: Path):
        for child in self._flow.get_children():
            child.get_style_context().remove_class("selected")
        btn.get_style_context().add_class("selected")
        self._selected_path = path
        self._set_image(self._current_img, str(path), -1, 180)

    # ── actions ───────────────────────────────────────────────

    def _apply_random(self, btn):
        if not self._all_images:
            return
        path = random.choice(self._all_images)
        self._selected_path = path
        self._set_image(self._current_img, str(path), -1, 180)
        self._apply_selected(btn)

    def _choose_dir(self, btn):
        chooser = Gtk.FileChooserNative.new(
            "Select Wallpaper Directory",
            self.get_toplevel(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            "Select",
            "Cancel",
        )
        chooser.set_current_folder(str(self._wallpaper_dir))

        def on_response(dialog, response):
            if response == Gtk.ResponseType.ACCEPT:
                folder = dialog.get_filename()
                if folder:
                    self._wallpaper_dir = Path(folder)
                    self._dir_label.set_text(str(self._wallpaper_dir))
                    self._dir_label.set_tooltip_text(str(self._wallpaper_dir))
                    build_index(self._wallpaper_dir, force=True)
                    self._load_thumbnails()
            dialog.destroy()

        chooser.connect("response", on_response)
        chooser.show()

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
        from ..theme import refresh_app_css

        refresh_app_css()
        return False
