"""Theme-gui: GTK3 glass window + monitor-style navigation.

A frameless, translucent, rounded window themed from hyprtk-bar's palette
(pywal / imported theme / manual) — the same look as the bar's system monitor.
A sidebar of glyph+label rows switches a Gtk.Stack of module pages.
"""
from __future__ import annotations

import logging

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .config import load as load_config, save as save_config  # noqa: E402
from .modules.bar import BarPage  # noqa: E402
from .modules.icons import IconsPage  # noqa: E402
from .modules.matuwall import MatuwallPage  # noqa: E402
from .modules.pywal import PywalPage  # noqa: E402
from .modules.rofi import RofiPage  # noqa: E402
from .modules.sddm import SddmPage  # noqa: E402
from .modules.swaylock import SwaylockPage  # noqa: E402
from .modules.wallpaper import WallpaperPage  # noqa: E402
from .theme import refresh_app_css  # noqa: E402
from .widgets import Glyph  # noqa: E402

log = logging.getLogger(__name__)

# (page key, title, glyph, page class)
PAGES: list[tuple[str, str, str, type]] = [
    ("wallpaper", "Wallpaper", "\uf03e", WallpaperPage),       # fa-picture-o
    ("pywal", "Pywal Colors", "\uf1fc", PywalPage),            # fa-paint-brush
    ("rofi", "Rofi Themes", "\uf0ca", RofiPage),               # fa-list-ul
    ("bar", "Bar Themes", "\uf0db", BarPage),                  # fa-columns
    ("matuwall", "Matuwall", "\uf07b", MatuwallPage),          # fa-folder-o
    ("swaylock", "Swaylock", "\uf023", SwaylockPage),          # fa-lock
    ("icons", "Icons", "\uf0c8", IconsPage),                   # fa-square
    ("sddm", "SDDM & GRUB", "\uf085", SddmPage),               # fa-cogs
]

DEFAULT_WIDTH = 1100
DEFAULT_HEIGHT = 700


class ThemeGuiApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="dev.hyprtk.theme_gui")
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        win = ThemeGuiWindow(application=app)
        win.present()


class ThemeGuiWindow(Gtk.Window):
    """Frameless, translucent glass window with a glyph sidebar + stack."""

    def __init__(self, application=None, **kwargs):
        super().__init__(**kwargs)
        self.set_application(application)
        self._cfg = load_config()
        self._pages: dict[str, object] = {}
        self._side_buttons: dict[str, Gtk.EventBox] = {}
        self._toast_label: Gtk.Label | None = None
        self._toast_timer = None

        # ── frameless glass window ─────────────────────────────
        self.set_title("Theme Manager")
        self.set_decorated(False)
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_default_size(
            int(self._cfg.get("window_width", DEFAULT_WIDTH)),
            int(self._cfg.get("window_height", DEFAULT_HEIGHT)),
        )
        self.set_size_request(720, 460)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("delete-event", self._on_delete)
        self.connect("key-press-event", self._on_key)

        refresh_app_css()

        # ── root glass panel ───────────────────────────────────
        self._overlay = Gtk.Overlay()
        self._root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._root.get_style_context().add_class("popup-box")
        self._root.get_style_context().add_class("tg-app")
        self._root.set_margin_top(12)
        self._root.set_margin_bottom(12)
        self._root.set_margin_start(12)
        self._root.set_margin_end(12)
        self._overlay.add(self._root)

        self._build_header()
        body = self._build_body()
        self._root.pack_start(body, True, True, 0)

        self._build_toast()
        self.add(self._overlay)

        # select the last-used page
        last = self._cfg.get("last_page", "wallpaper")
        self._select_page(last if last in self._pages else "wallpaper")

    # ── header ────────────────────────────────────────────────

    def _build_header(self):
        header = Gtk.EventBox()
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="Theme Manager", xalign=0)
        title.get_style_context().add_class("mc-title")
        row.pack_start(title, True, True, 0)

        close = Gtk.Button(label="\u00d7")
        close.get_style_context().add_class("mc-close")
        close.set_relief(Gtk.ReliefStyle.NONE)
        close.connect("clicked", lambda *_: self.close())
        row.pack_start(close, False, False, 0)

        header.add(row)
        header.connect("button-press-event", self._on_header_press)
        self._root.pack_start(header, False, False, 0)

    def _on_header_press(self, _widget, event) -> bool:
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.begin_move_drag(
                event.button, int(event.x_root), int(event.y_root), event.time
            )
            return True
        return False

    def _on_key(self, _widget, event) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    # ── sidebar + stack ───────────────────────────────────────

    def _build_body(self):
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sidebar.get_style_context().add_class("mc-sidebar")
        sidebar.set_size_request(176, -1)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(120)

        for key, title, glyph, cls in PAGES:
            page = cls()
            page.set_vexpand(True)
            self._pages[key] = page
            self._stack.add_named(page, key)
            sidebar.pack_start(
                self._build_side_button(key, glyph, title), False, False, 0
            )

        body.pack_start(sidebar, False, False, 0)
        body.pack_start(self._stack, True, True, 0)
        return body

    def _build_side_button(self, key: str, glyph: str, label_text: str) -> Gtk.EventBox:
        ev = Gtk.EventBox()
        ev.set_visible_window(False)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.get_style_context().add_class("mc-sidebar-button")
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_start(8)
        box.set_margin_end(8)

        icon = Glyph(glyph, "mc-icon")
        icon.set_pixel_size(14)
        box.pack_start(icon, False, False, 0)

        lbl = Gtk.Label(label=label_text, xalign=0)
        lbl.get_style_context().add_class("mc-sidebar-label")
        box.pack_start(lbl, True, True, 0)

        ev.add(box)
        ev.connect("enter-notify-event", self._on_side_enter, box)
        ev.connect("leave-notify-event", self._on_side_leave, box)
        ev.connect("button-press-event",
                   lambda _w, _e, k=key: self._on_side_press(k) or False)
        self._side_buttons[key] = box
        return ev

    def _on_side_enter(self, _w, _e, box):
        box.get_style_context().add_class("hover")
        return False

    def _on_side_leave(self, _w, _e, box):
        box.get_style_context().remove_class("hover")
        return False

    def _on_side_press(self, key: str) -> bool:
        self._select_page(key)
        return True

    def _select_page(self, key: str):
        for k, box in self._side_buttons.items():
            ctx = box.get_style_context()
            if k == key:
                ctx.add_class("active")
            else:
                ctx.remove_class("active")
        self._stack.set_visible_child_name(key)
        page = self._pages.get(key)
        if page is not None and hasattr(page, "on_shown"):
            page.on_shown()
        self._cfg["last_page"] = key
        save_config(self._cfg)

    # ── toast ─────────────────────────────────────────────────

    def _build_toast(self):
        self._toast_label = Gtk.Label(label="")
        self._toast_label.get_style_context().add_class("toast-label")
        self._toast_label.set_halign(Gtk.Align.CENTER)
        self._toast_label.set_valign(Gtk.Align.END)
        self._toast_label.set_margin_bottom(18)
        self._toast_label.set_visible(False)
        self._overlay.add_overlay(self._toast_label)

    def _show_toast(self, message: str, timeout: int = 2):
        if self._toast_timer is not None:
            GLib.source_remove(self._toast_timer)
            self._toast_timer = None
        self._toast_label.set_text(message)
        self._toast_label.set_visible(True)
        self._toast_timer = GLib.timeout_add_seconds(
            max(1, timeout), self._hide_toast
        )

    def _hide_toast(self) -> bool:
        self._toast_timer = None
        self._toast_label.set_visible(False)
        return GLib.SOURCE_REMOVE

    # ── persistence ───────────────────────────────────────────

    def _on_delete(self, *_args) -> bool:
        w, h = self.get_size()
        min_w, _min_h = self.get_size_request()
        if w >= min_w:
            self._cfg["window_width"] = w
            self._cfg["window_height"] = h
        save_config(self._cfg)
        return False
