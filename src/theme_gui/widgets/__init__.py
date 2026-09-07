"""Shared widget utilities and base classes."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


def remove_all_children(widget):
    """Remove all children from a GTK4 widget."""
    while True:
        child = widget.get_first_child()
        if child is None:
            break
        widget.remove(child)


def show_toast(widget: Gtk.Widget, message: str, timeout: int = 2):
    """Walk up the widget tree to find a ToastOverlay and show a toast."""
    toast = Adw.Toast(title=message)
    toast.set_timeout(timeout)
    w = widget
    while w is not None:
        if isinstance(w, Adw.ToastOverlay):
            w.add_toast(toast)
            return
        parent = w.get_parent() if hasattr(w, "get_parent") else None
        w = parent


class BasePage(Adw.NavigationPage):
    """Base class for all theme-gui pages.

    Provides standard ToolbarView + HeaderBar + scrollable vertical box layout.
    Subclasses should use ``self._box`` to add content.
    """

    def __init__(self, title: str, **kwargs):
        super().__init__(title=title, **kwargs)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._box.set_margin_top(12)
        self._box.set_margin_bottom(12)
        self._box.set_margin_start(12)
        self._box.set_margin_end(12)

        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_child(self._box)
        self._scroll.set_vexpand(True)

        toolbar.set_content(self._scroll)
        self.set_child(toolbar)
