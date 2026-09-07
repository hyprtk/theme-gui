"""Clickable grid displaying the 16-color pywal palette (GTK3)."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from . import remove_all_children  # noqa: E402
from ..colors import get_color_name, hex_to_rgb  # noqa: E402


class ColorGrid(Gtk.Box):
    """Displays the 16-color pywal palette as a clickable grid of swatches."""

    def __init__(self, colors: dict[str, str] | None = None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6, **kwargs)
        self._buttons: list[Gtk.Button] = []
        self._providers: list[Gtk.CssProvider] = []
        self._callback = None
        if colors:
            self.set_colors(colors)

    def set_colors(self, colors: dict[str, str]):
        remove_all_children(self)
        self._buttons.clear()
        self._providers.clear()

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for i in range(16):
            key = f"color{i}"
            hex_val = colors.get(key, "#000000")
            name = get_color_name(i)
            r, g, b = hex_to_rgb(hex_val)

            btn = Gtk.Button()
            btn.set_tooltip_text(f"{name}\n{hex_val}")
            btn.set_size_request(40, 40)

            provider = Gtk.CssProvider()
            css = (
                f"button {{ background: {hex_val}; "
                f"border-radius: 50%; min-width: 34px; min-height: 34px; "
                f"border: 1px solid rgba(255,255,255,0.15); }}"
            )
            provider.load_from_data(css.encode())
            btn.get_style_context().add_provider(
                provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            self._providers.append(provider)

            idx = i
            btn.connect("clicked", lambda b, n=idx: self._on_click(n))
            self._buttons.append(btn)
            if i == 8:
                self.pack_start(row, False, False, 0)
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.pack_start(btn, False, False, 0)
        self.pack_start(row, False, False, 0)
        self.show_all()

    def _on_click(self, index: int):
        if self._callback:
            self._callback(index, f"color{index}")

    def connect_color_selected(self, callback):
        self._callback = callback
