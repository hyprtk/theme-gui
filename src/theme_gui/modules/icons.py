"""Icon theme manager with pywal auto-color and manual presets (GTK3)."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")

from gi.repository import GdkPixbuf, GLib, Gtk, Pango  # noqa: E402

from .. import paths  # noqa: E402
from ..widgets import BasePage, remove_all_children, show_toast  # noqa: E402

log = logging.getLogger(__name__)

POST_ACTION_DELAY_MS = 2000
ICON_THEME_DIR = Path.home() / ".local" / "share" / "icons" / "Papirus-Dark" / "48x48" / "places"
PAPIRUS_FOLDERS = Path.home() / ".local" / "bin" / "papirus-folders"
PAPIRUS_FOLDERS_SH = Path.home() / ".local" / "share" / "icons" / "papirus-folders.sh"
ICON_CACHE_THEME_DIRS = [
    Path.home() / ".local" / "share" / "icons" / "Papirus-Dark",
    Path.home() / ".local" / "share" / "icons" / "Papirus",
    Path.home() / ".local" / "share" / "icons" / "Papirus-Light",
]

_PREVIEW_ICONS = [
    ("folder-{color}-desktop.svg", "Desktop"),
    ("folder-{color}-documents.svg", "Documents"),
    ("folder-{color}-downloads.svg", "Downloads"),
    ("folder-{color}-music.svg", "Music"),
    ("folder-{color}-pictures.svg", "Pictures"),
    ("folder-{color}-projects.svg", "Projects"),
    ("folder-{color}-videos.svg", "Videos"),
]

_COLOR_PRESETS = [
    ("hyprtk-adwaita", "adwaita"),
    ("hyprtk-black", "black"),
    ("hyprtk-blue", "blue"),
    ("hyprtk-bluegrey", "bluegrey"),
    ("hyprtk-breeze", "breeze"),
    ("hyprtk-brown", "brown"),
    ("hyprtk-carmine", "carmine"),
    ("hyprtk-cyan", "cyan"),
    ("hyprtk-darkcyan", "darkcyan"),
    ("hyprtk-deeporange", "deeporange"),
    ("hyprtk-green", "green"),
    ("hyprtk-grey", "grey"),
    ("hyprtk-indigo", "indigo"),
    ("hyprtk-magenta", "magenta"),
    ("hyprtk-nordic", "nordic"),
    ("hyprtk-orange", "orange"),
    ("hyprtk-palebrown", "palebrown"),
    ("hyprtk-paleorange", "paleorange"),
    ("hyprtk-pink", "pink"),
    ("hyprtk-red", "red"),
    ("hyprtk-teal", "teal"),
    ("hyprtk-violet", "violet"),
    ("hyprtk-white", "white"),
    ("hyprtk-yaru", "yaru"),
    ("hyprtk-yellow", "yellow"),
]


def _detect_current_color() -> str:
    if not ICON_THEME_DIR.exists():
        return ""
    folder_svg = ICON_THEME_DIR / "folder.svg"
    if folder_svg.is_symlink():
        name = Path(os.readlink(str(folder_svg))).stem
        return name.replace("folder-", "")
    for _display_name, papirus_color in _COLOR_PRESETS:
        candidate = ICON_THEME_DIR / f"folder-{papirus_color}-pictures.svg"
        if candidate.exists():
            return papirus_color
    return ""


def _run_papirus_folders(*args: str, script: bool = False) -> bool:
    try:
        if script and PAPIRUS_FOLDERS_SH.is_file():
            subprocess.Popen(
                ["bash", str(PAPIRUS_FOLDERS_SH), *args],
                start_new_session=True,
            )
        elif PAPIRUS_FOLDERS.is_file():
            subprocess.Popen(
                [str(PAPIRUS_FOLDERS), *args],
                start_new_session=True,
            )
        else:
            return False
        return True
    except FileNotFoundError as exc:
        log.warning("papirus-folders failed: %s", exc)
        return False


def _update_icon_cache():
    def _do_update():
        for theme_dir in ICON_CACHE_THEME_DIRS:
            if theme_dir.exists():
                try:
                    subprocess.run(
                        ["gtk-update-icon-cache", "-qf", str(theme_dir)],
                        capture_output=True,
                        timeout=30,
                    )
                except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                    log.warning("icon cache update failed: %s", exc)
        return False

    GLib.idle_add(_do_update)


def _load_svg(path: Path, size: int):
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(path), size, size, True
        )
        img = Gtk.Image.new_from_pixbuf(pb)
        return img
    except Exception:
        return None


class IconsPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Icons", **kwargs)
        self._applying = False

        preview_sec = self.section("Current Folder Icons")
        self._preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._preview_box.set_halign(Gtk.Align.START)
        preview_sec.pack_start(self._preview_box, False, False, 0)
        self._preview_color_label = Gtk.Label(label="", xalign=0)
        self._preview_color_label.get_style_context().add_class("dim-label")
        preview_sec.pack_start(self._preview_color_label, False, False, 0)

        auto_sec = self.section("Pywal Auto-Color")
        auto_desc = Gtk.Label(
            label="Automatically match papirus folder color to pywal color4. "
            "Uses Euclidean distance to find the closest preset.",
            xalign=0,
            wrap=True,
        )
        auto_desc.get_style_context().add_class("dim-label")
        auto_sec.pack_start(auto_desc, False, False, 0)
        apply_auto_btn = self.primary_button("Apply Pywal Color Match")
        apply_auto_btn.connect("clicked", self._apply_auto)
        auto_sec.pack_start(apply_auto_btn, False, False, 0)

        manual_sec = self.section("Manual Folder Color")
        self._preset_buttons: dict[str, Gtk.Button] = {}
        grid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        current_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for i, (display_name, papirus_color) in enumerate(_COLOR_PRESETS):
            if i % 7 == 0 and i > 0:
                grid.pack_start(current_row, False, False, 0)
                current_row = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL, spacing=8
                )
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.set_halign(Gtk.Align.CENTER)
            btn = Gtk.Button()
            btn.get_style_context().add_class("flat")
            btn.set_size_request(40, 40)
            icon_file = ICON_THEME_DIR / f"folder-{papirus_color}-pictures.svg"
            img = _load_svg(icon_file, 36) if icon_file.exists() else None
            if img is not None:
                btn.add(img)
            else:
                btn.add(Gtk.Label(label=display_name[0].upper()))
            btn.connect(
                "clicked", lambda b, c=papirus_color: self._apply_preset(c)
            )
            self._preset_buttons[display_name] = btn
            col.pack_start(btn, False, False, 0)
            lbl = Gtk.Label(label=display_name)
            lbl.set_markup(f"<small>{display_name}</small>")
            col.pack_start(lbl, False, False, 0)
            current_row.pack_start(col, False, False, 0)
        grid.pack_start(current_row, False, False, 0)
        manual_sec.pack_start(grid, False, False, 0)

        # custom hex
        custom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        custom_lbl = Gtk.Label(label="Custom hex color", xalign=0)
        custom_box.pack_start(custom_lbl, False, False, 0)
        self._custom_entry = Gtk.Entry()
        self._custom_entry.set_text("#2196F3")
        self._custom_entry.set_hexpand(True)
        custom_box.pack_start(self._custom_entry, True, True, 0)
        apply_custom_btn = self.primary_button("Apply")
        apply_custom_btn.connect("clicked", self._apply_custom)
        custom_box.pack_start(apply_custom_btn, False, False, 0)
        manual_sec.pack_start(custom_box, False, False, 0)

        self._load_current()

    def on_shown(self):
        self._load_current()

    def _load_current(self):
        color = _detect_current_color()
        self._preview_color_label.set_text(f"Current color: {color or 'unknown'}")
        self._refresh_preview(color)

    def _refresh_preview(self, color: str):
        remove_all_children(self._preview_box)
        if not ICON_THEME_DIR.exists():
            lbl = Gtk.Label(label="(icon theme not found)")
            self._preview_box.pack_start(lbl, False, False, 0)
            return
        for icon_template, label_text in _PREVIEW_ICONS:
            icon_name = icon_template.replace("{color}", color)
            icon_path = ICON_THEME_DIR / icon_name
            if not icon_path.exists():
                fallback_name = icon_template.replace(f"-{color}", "")
                icon_path = ICON_THEME_DIR / fallback_name
            if not icon_path.exists():
                continue
            item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            item.set_halign(Gtk.Align.CENTER)
            img = _load_svg(icon_path, 40)
            if img is None:
                continue
            item.pack_start(img, False, False, 0)
            lbl = Gtk.Label(label=label_text)
            lbl.set_markup(f"<small>{label_text}</small>")
            item.pack_start(lbl, False, False, 0)
            self._preview_box.pack_start(item, False, False, 0)
        self._preview_box.show_all()

    def _apply_auto(self, btn):
        script = str(paths.CHANGE_ICONS_SH)
        if Path(script).is_file():
            try:
                subprocess.Popen(["bash", script], start_new_session=True)
                GLib.timeout_add(POST_ACTION_DELAY_MS, self._post_color_change)
                show_toast(
                    self,
                    "Icon Theme - pywal color applied\n"
                    "Press F5 in File Manager to refresh",
                    timeout=5,
                )
            except FileNotFoundError:
                show_toast(self, "Failed to run icon script", timeout=4)

    def _apply_preset(self, color_name: str):
        if self._applying:
            return
        self._applying = True
        ok = _run_papirus_folders(
            "-C", color_name, "-t", "Papirus-Dark",
            script=PAPIRUS_FOLDERS_SH.is_file(),
        )
        if ok:
            GLib.timeout_add(POST_ACTION_DELAY_MS, self._post_color_change)
            show_toast(self, f"Icon Theme - {color_name} applied", timeout=5)
        else:
            show_toast(self, "papirus-folders not found", timeout=4)
        self._applying = False

    def _post_color_change(self):
        self._fix_variant_symlinks()
        _update_icon_cache()
        self._load_current()
        return False

    def _fix_variant_symlinks(self):
        if not ICON_THEME_DIR.exists():
            return
        folder_svg = ICON_THEME_DIR / "folder.svg"
        if folder_svg.is_symlink():
            color = Path(os.readlink(str(folder_svg))).stem.replace("folder-", "")
        else:
            return
        if not color:
            return
        sizes = ["22x22", "24x24", "32x32", "48x48", "64x64",
                 "22x22@2x", "24x24@2x", "32x32@2x", "48x48@2x", "64x64@2x"]
        theme_root = ICON_THEME_DIR.parent.parent
        for size in sizes:
            places = theme_root / size / "places"
            if not places.exists():
                continue
            for color_file in places.glob(f"folder-{color}-*.svg"):
                generic_name = color_file.name.replace(f"-{color}", "", 1)
                generic_path = places / generic_name
                if generic_path == color_file:
                    continue
                if generic_path.exists() or generic_path.is_symlink():
                    generic_path.unlink()
                os.symlink(color_file.name, str(generic_path))
            if color.startswith("hyprtk-"):
                base_color = color[len("hyprtk-"):]
                for variant in ("desktop", "home", "home-open"):
                    user_generic = places / f"user-{variant}.svg"
                    user_target = f"user-{base_color}-{variant}.svg"
                    user_target_path = places / user_target
                    if user_target_path.exists():
                        if user_generic.exists() or user_generic.is_symlink():
                            current = (
                                os.readlink(str(user_generic))
                                if user_generic.is_symlink()
                                else None
                            )
                            if current != user_target:
                                user_generic.unlink()
                                os.symlink(user_target, str(user_generic))
                        else:
                            os.symlink(user_target, str(user_generic))

    def _apply_custom(self, btn):
        hex_val = self._custom_entry.get_text().strip()
        if not hex_val.startswith("#"):
            hex_val = f"#{hex_val}"
        if len(hex_val) != 7:
            show_toast(self, "Invalid hex color (use #RRGGBB)", timeout=3)
            return
        ok = _run_papirus_folders(
            "-C", hex_val.lstrip("#"), "--theme", "Papirus-Dark",
        )
        if ok:
            GLib.timeout_add(POST_ACTION_DELAY_MS, self._post_color_change)
            show_toast(self, f"Icon Theme - {hex_val} applied", timeout=5)
        else:
            show_toast(self, "papirus-folders not found", timeout=4)
