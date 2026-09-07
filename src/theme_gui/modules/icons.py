"""Icon theme manager with pywal auto-color and manual presets."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from gi.repository import Adw, GLib, Gtk

from .. import paths
from ..widgets import BasePage, remove_all_children, show_toast

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
        target = os.readlink(str(folder_svg))
        name = Path(target).stem
        return name.replace("folder-", "")
    for _display_name, papirus_color in _COLOR_PRESETS:
        candidate = ICON_THEME_DIR / f"folder-{papirus_color}-pictures.svg"
        if candidate.exists():
            return papirus_color
    return ""


def _run_papirus_folders(*args: str, script: bool = False) -> bool:
    """Run papirus-folders with error handling. Returns True on success."""
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
    """Refresh icon cache in background (non-blocking)."""
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


class IconsPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Icons", **kwargs)
        self._applying = False

        # current icons preview
        preview_title = Gtk.Label(label="Current Folder Icons")
        preview_title.add_css_class("heading")
        preview_title.set_xalign(0)
        self._box.append(preview_title)

        self._preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._preview_box.set_halign(Gtk.Align.START)
        self._box.append(self._preview_box)

        self._preview_color_label = Gtk.Label(label="")
        self._preview_color_label.set_xalign(0)
        self._box.append(self._preview_color_label)

        sep0 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self._box.append(sep0)

        # pywal auto mode
        auto_title = Gtk.Label(label="Pywal Auto-Color")
        auto_title.add_css_class("heading")
        auto_title.set_xalign(0)
        self._box.append(auto_title)

        auto_desc = Gtk.Label(
            label="Automatically match papirus folder color to pywal color4. "
            "Uses Euclidean distance to find the closest preset."
        )
        auto_desc.set_xalign(0)
        auto_desc.set_wrap(True)
        self._box.append(auto_desc)

        apply_auto_btn = Gtk.Button(label="Apply Pywal Color Match")
        apply_auto_btn.add_css_class("suggested-action")
        apply_auto_btn.connect("clicked", self._apply_auto)
        self._box.append(apply_auto_btn)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self._box.append(sep)

        # manual color picker
        manual_title = Gtk.Label(label="Manual Folder Color")
        manual_title.add_css_class("heading")
        manual_title.set_xalign(0)
        self._box.append(manual_title)

        self._preset_buttons: dict[str, Gtk.Button] = {}
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)

        for i, (display_name, papirus_color) in enumerate(_COLOR_PRESETS):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.set_halign(Gtk.Align.CENTER)

            btn = Gtk.Button()
            btn.add_css_class("flat")
            btn.set_size_request(48, 48)

            icon_file = ICON_THEME_DIR / f"folder-{papirus_color}-pictures.svg"
            if icon_file.exists():
                img = Gtk.Image.new_from_file(str(icon_file))
                img.set_pixel_size(48)
                btn.set_child(img)
            else:
                btn.set_child(Gtk.Label(label=display_name[0].upper()))

            btn.connect("clicked", lambda b, c=papirus_color: self._apply_preset(c))
            self._preset_buttons[display_name] = btn
            col.append(btn)

            lbl = Gtk.Label()
            lbl.set_markup(f'<small>{display_name}</small>')
            col.append(lbl)

            grid.attach(col, i % 7, i // 7, 1, 1)

        self._box.append(grid)

        # custom hex input
        custom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._custom_entry = Adw.EntryRow(title="Custom hex color")
        self._custom_entry.set_text("#2196F3")
        custom_box.append(self._custom_entry)

        apply_custom_btn = Gtk.Button(label="Apply")
        apply_custom_btn.connect("clicked", self._apply_custom)
        custom_box.append(apply_custom_btn)
        self._box.append(custom_box)

        self.connect("map", lambda w: self._load_current())

    def _load_current(self):
        color = _detect_current_color()
        self._preview_color_label.set_text(f"Current color: {color or 'unknown'}")
        self._refresh_preview(color)

    def _refresh_preview(self, color: str):
        remove_all_children(self._preview_box)

        if not ICON_THEME_DIR.exists():
            lbl = Gtk.Label(label="(icon theme not found)")
            self._preview_box.append(lbl)
            return

        for icon_template, label_text in _PREVIEW_ICONS:
            icon_name = icon_template.replace("{color}", color)
            icon_path = ICON_THEME_DIR / icon_name
            if not icon_path.exists():
                fallback_name = icon_template.replace(f"-{color}", "")
                icon_path = ICON_THEME_DIR / fallback_name
            if not icon_path.exists():
                continue

            icon_box = Gtk.Box()
            icon_box.set_size_request(48, 48)
            icon_box.set_halign(Gtk.Align.CENTER)
            icon_box.set_valign(Gtk.Align.CENTER)

            img = Gtk.Image.new_from_file(str(icon_path))
            img.set_pixel_size(48)
            icon_box.append(img)

            item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            item.set_halign(Gtk.Align.CENTER)
            item.append(icon_box)

            lbl = Gtk.Label(label=label_text)
            lbl.set_markup(f'<small>{label_text}</small>')
            item.append(lbl)

            self._preview_box.append(item)

    def _apply_auto(self, btn):
        script = str(paths.CHANGE_ICONS_SH)
        if Path(script).is_file():
            try:
                subprocess.Popen(["bash", script], start_new_session=True)
                GLib.timeout_add(POST_ACTION_DELAY_MS, self._post_color_change)
                show_toast(self, "Icon Theme - pywal color applied\nPress F5 in File Manager to refresh", timeout=5)
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
            target = os.readlink(str(folder_svg))
            color = Path(target).stem.replace("folder-", "")
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
                            current = os.readlink(str(user_generic)) if user_generic.is_symlink() else None
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
