"""Theme-gui GTK4/Adwaita application."""
from __future__ import annotations

import os
import logging
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk

from .colors import contrast_fg, parse_wal_colors
from .config import load as load_config, save as save_config
from .modules.icons import IconsPage
from .modules.matuwall import MatuwallPage
from .modules.pywal import PywalPage
from .modules.rofi import RofiPage
from .modules.sddm import SddmPage
from .modules.swaylock import SwaylockPage
from .modules.wallpaper import WallpaperPage
from .modules.waybar import WaybarPage

# ── Page registry (single source of truth) ──────────────────────────────────

PAGES: dict[str, tuple[str, str, type]] = {
    "wallpaper": ("Wallpaper", "image-x-generic-symbolic", WallpaperPage),
    "pywal": ("Pywal Colors", "colors-symbolic", PywalPage),
    "rofi": ("Rofi Themes", "view-app-grid-symbolic", RofiPage),
    "waybar": ("Waybar Themes", "view-dual-symbolic", WaybarPage),
    "matuwall": ("Matuwall", "folder-pictures-symbolic", MatuwallPage),
    "swaylock": ("Swaylock", "system-lock-screen-symbolic", SwaylockPage),
    "icons": ("Icons", "folder-symbolic", IconsPage),
    "sddm": ("SDDM & GRUB", "system-os-install-symbolic", SddmPage),
}


def build_app_css() -> str:
    """Build CSS with pywal colors for buttons and UI elements."""
    colors = parse_wal_colors()
    bg = colors.get("background", "#1b0b0b")
    fg = colors.get("foreground", "#c6c2c2")
    color1 = colors.get("color1", "#69443B")
    color4 = colors.get("color4", "#A6522D")
    color5 = colors.get("color5", "#A05030")
    color6 = colors.get("color6", "#A16A52")

    fg_on_color5 = contrast_fg(color5)
    fg_on_color4 = contrast_fg(color4)
    fg_on_color6 = contrast_fg(color6)
    fg_on_color1 = contrast_fg(color1)

    return f"""
    @define-color accent_color {color5};
    @define-color accent_bg_color {color5};
    @define-color accent_fg_color {fg};
    @define-color window_bg_color {bg};
    @define-color window_fg_color {fg};
    @define-color headerbar_bg_color {bg};
    @define-color headerbar_fg_color {fg};
    @define-color card_bg_color alpha({bg}, 0.6);
    @define-color card_fg_color {fg};
    @define-color dialog_bg_color {bg};
    @define-color dialog_fg_color {fg};
    @define-color popover_bg_color {bg};
    @define-color popover_fg_color {fg};
    @define-color shade_color alpha(#000000, 0.36);
    @define-color sidebar_bg_color {bg};
    @define-color sidebar_fg_color {fg};
    @define-color sidebar_shade_color alpha(#000000, 0.36);
    @define-color view_bg_color {bg};
    @define-color view_fg_color {fg};
    @define-color success_color {color6};
    @define-color success_bg_color {color6};
    @define-color success_fg_color {fg_on_color6};
    @define-color warning_color {color1};
    @define-color warning_bg_color {color1};
    @define-color warning_fg_color {fg_on_color1};
    @define-color error_color #e01b24;
    @define-color error_bg_color #e01b24;
    @define-color error_fg_color #ffffff;
    @define-color destructive_color #e01b24;
    @define-color destructive_bg_color #e01b24;
    @define-color destructive_fg_color #ffffff;
    @define-color suggested_color {color4};
    @define-color suggested_bg_color {color4};
    @define-color suggested_fg_color {fg_on_color4};
    @define-color window_bg {bg};
    @define-color window_fg {fg};
    @define-color view_bg {bg};
    @define-color view_fg {fg};

    /* Override Adw suggested-action buttons (pywal accent) */
    button.suggested-action, button.suggested-action:hover {{
        background: {color5};
        color: {fg_on_color5};
        border-color: {color5};
    }}
    button.suggested-action:disabled {{
        background: alpha({color5}, 0.5);
    }}

    /* Override Adw flat buttons */
    button.flat {{
        color: {fg};
    }}
    button.flat:hover {{
        background: alpha({fg}, 0.08);
    }}

    /* Focus indicators for keyboard navigation */
    button:focus-visible {{
        outline: 2px solid {color5};
        outline-offset: 2px;
    }}
    entry:focus-visible {{
        outline: 2px solid {color5};
        outline-offset: 2px;
    }}

    /* Sidebar rows */
    .sidebar-row {{
        border-radius: 8px;
        margin: 2px 0;
        padding: 4px 8px;
    }}
    .sidebar-row:hover {{
        background: alpha({fg}, 0.08);
    }}
    .sidebar-row.active {{
        background: alpha({color5}, 0.15);
        font-weight: bold;
    }}

    /* Entry fields */
    entry {{
        background: alpha({fg}, 0.08);
        color: {fg};
        border-color: alpha({fg}, 0.15);
        border-radius: 8px;
    }}
    entry:focus {{
        border-color: {color5};
    }}

    /* Switches — rounded pill track */
    switch {{
        border-radius: 12px;
        min-height: 24px;
        min-width: 44px;
    }}
    switch:checked {{
        background: {color5};
    }}

    /* Random wallpaper button — pywal accent */
    .random-btn {{
        color: {color6};
        border-color: alpha({color6}, 0.4);
    }}
    .random-btn:hover {{
        background: alpha({color6}, 0.15);
        color: {color6};
    }}

    /* Loading spinner */
    .loading-spinner {{
        color: {color5};
    }}
    """


class ThemeGuiApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.hyprtk.theme_gui")
        self.connect("activate", self._on_activate)
        self.connect("startup", self._on_startup)
        self._cfg = load_config()

    def _on_startup(self, app):
        sm = Adw.StyleManager.get_default()
        sm.set_color_scheme(Adw.ColorScheme.DEFAULT)

        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(build_app_css().encode())
        except GLib.Error as exc:
            logging.getLogger(__name__).warning("failed to load app css: %s", exc)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )

    def _on_activate(self, app):
        win = ThemeGuiWindow(application=app)
        win.set_config(self._cfg)
        win.present()


class ThemeGuiWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cfg: dict = {}
        self._pages: dict[str, Adw.NavigationPage] = {}
        self._sidebar_btns: dict[str, Gtk.Button] = {}

        self.set_title("Theme Manager")
        self.set_default_size(1100, 700)
        self.set_size_request(600, 400)

        # ── navigation split view ─────────────────────────────
        nav = Adw.NavigationSplitView()
        nav.set_sidebar_width_fraction(0.3)

        # ── sidebar ───────────────────────────────────────────
        sidebar_page = Adw.NavigationPage(title="Themes", tag="sidebar")

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_header = Adw.HeaderBar()
        sidebar_box.append(sidebar_header)

        sidebar_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sidebar_list.set_margin_top(8)

        self._nav = nav
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._stack.set_transition_duration(200)

        for tag, (title, icon, cls) in PAGES.items():
            page = cls()
            self._pages[tag] = page
            self._stack.add_named(page, tag)

            btn = Gtk.Button()
            btn.add_css_class("flat")
            btn.add_css_class("sidebar-item")
            btn.set_halign(Gtk.Align.FILL)
            btn.set_child(self._make_sidebar_row(title, icon))
            btn._page_tag = tag
            btn.connect("clicked", self._on_sidebar_click)
            sidebar_list.append(btn)
            self._sidebar_btns[tag] = btn

        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_child(sidebar_list)
        sidebar_scroll.set_vexpand(True)
        sidebar_box.append(sidebar_scroll)

        # logo at bottom of sidebar
        logo_path = str(Path(__file__).parent / "arch_logo.png")
        if os.path.isfile(logo_path):
            logo = Gtk.Picture()
            logo.set_filename(logo_path)
            logo.set_content_fit(Gtk.ContentFit.CONTAIN)
            logo.set_halign(Gtk.Align.CENTER)
            logo.set_valign(Gtk.Align.END)
            logo.set_margin_top(8)
            logo.set_margin_bottom(25)
            logo.set_margin_start(12)
            logo.set_margin_end(12)
            sidebar_box.append(logo)

        sidebar_page.set_child(sidebar_box)

        # ── content ───────────────────────────────────────────
        content_page = Adw.NavigationPage(title="Theme Manager", tag="content")
        content_page.set_child(self._stack)

        nav.set_sidebar(sidebar_page)
        nav.set_content(content_page)

        overlay = Adw.ToastOverlay()
        overlay.set_child(nav)
        self.set_content(overlay)

    def set_config(self, cfg: dict):
        self._cfg = cfg
        self.set_default_size(
            cfg.get("window_width", 1100),
            cfg.get("window_height", 700),
        )
        last_page = cfg.get("last_page", "wallpaper")
        self._select_page(last_page)

    def _make_sidebar_row(self, title: str, icon_name: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)

        img = Gtk.Image.new_from_icon_name(icon_name)
        img.set_pixel_size(20)
        box.append(img)

        label = Gtk.Label(label=title)
        label.set_xalign(0)
        box.append(label)

        return box

    def _on_sidebar_click(self, btn):
        tag = btn._page_tag
        self._select_page(tag)

    def _select_page(self, tag: str):
        self._stack.set_visible_child_name(tag)
        # update active indicator on sidebar
        for t, b in self._sidebar_btns.items():
            if t == tag:
                b.add_css_class("active")
            else:
                b.remove_css_class("active")
        # save config directly without re-reading from disk
        self._cfg["last_page"] = tag
        save_config(self._cfg)

    def do_close_request(self):
        w, h = self.get_default_size()
        self._cfg["window_width"] = w
        self._cfg["window_height"] = h
        save_config(self._cfg)
        return False
