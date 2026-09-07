"""Shared GTK3 widgets and helpers for theme-gui (monitor-style chrome)."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import Gtk, Pango  # noqa: E402

GLYPH_FONT = "Symbols Nerd Font"


class Glyph(Gtk.Label):
    """A Nerd Font glyph rendered at an exact pixel size.

    The system font has no PUA glyphs (and maps them to the wrong characters),
    so glyphs always render with a dedicated Nerd Font family; the size is set
    in device units (pixels) to match Gtk.Image pixel sizes.
    """

    def __init__(self, codepoint: str, css_class: str = "", font: str = ""):
        super().__init__(label=codepoint)
        self._font = (font or "").strip() or GLYPH_FONT
        if css_class:
            self.get_style_context().add_class(css_class)
        self.set_pixel_size(16)

    def set_pixel_size(self, size: int) -> None:
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_family_new(self._font))
        attrs.insert(Pango.attr_size_new_absolute(int(max(size, 10)) * Pango.SCALE))
        self.set_attributes(attrs)


def remove_all_children(widget) -> None:
    """Remove every child of a GTK3 container."""
    for child in list(widget.get_children()):
        widget.remove(child)


def show_toast(widget: Gtk.Widget, message: str, timeout: int = 2) -> None:
    """Show a themed in-window toast, walking up to the ThemeGuiWindow.

    Keeps the same call shape as the old Adw.Toast API so modules can report
    results without caring which window hosts them.
    """
    w = widget
    while w is not None:
        handler = getattr(w, "_show_toast", None)
        if callable(handler):
            handler(message, timeout)
            return
        w = w.get_parent()


def _scaled_pixbuf(path: str, width: int, height: int):
    """Load an image at path, scaled to fit within width x height (contain)."""
    import os

    if not path or not os.path.isfile(path):
        return None
    try:
        from gi.repository import GdkPixbuf

        return GdkPixbuf.Pixbuf.new_from_file_at_scale(
            path, width, height, True
        )
    except Exception:
        return None


class BasePage(Gtk.Box):
    """A monitor-style page: page title + scrolled vertical body.

    Subclasses build into ``self.body`` (a ``Gtk.Box``). ``section(title)``
    creates a titled glass card that stays visually consistent with the bar's
    system monitor.
    """

    def __init__(self, title: str, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._page_title = title
        self.set_hexpand(True)
        self.set_vexpand(True)

        head = Gtk.Label(label=title, xalign=0)
        head.get_style_context().add_class("mc-page-title")
        head.set_margin_bottom(2)
        self.pack_start(head, False, False, 0)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.body.set_margin_top(2)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.add(self.body)
        self.pack_start(scroller, True, True, 0)

    # ── helpers ───────────────────────────────────────────────

    def section(self, title: str | None = None) -> Gtk.Box:
        """Create and add a glass card; optional small section title."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.get_style_context().add_class("settings-section")
        box.set_hexpand(True)
        if title:
            head = Gtk.Label(label=title.upper(), xalign=0)
            head.get_style_context().add_class("settings-section-title")
            box.pack_start(head, False, False, 0)
        self.body.pack_start(box, False, False, 0)
        return box

    def add_label(self, text: str, dim: bool = False, wrap: bool = False) -> Gtk.Label:
        lbl = Gtk.Label(label=text, xalign=0)
        if wrap:
            lbl.set_line_wrap(True)
        if dim:
            lbl.get_style_context().add_class("dim-label")
        self.body.pack_start(lbl, False, False, 0)
        return lbl

    def primary_button(self, label: str) -> Gtk.Button:
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class("settings-apply")
        return btn

    def flat_button(self, label: str) -> Gtk.Button:
        btn = Gtk.Button(label=label)
        btn.get_style_context().add_class("flat")
        return btn

    def toast(self, message: str, timeout: int = 2) -> None:
        show_toast(self, message, timeout)

    # ── actions triggered on page show ────────────────────────

    def on_shown(self) -> None:
        """Called when the page becomes visible (subclasses may refresh)."""
