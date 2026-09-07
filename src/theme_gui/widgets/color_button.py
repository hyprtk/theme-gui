"""GTK3 color picker button + dialog for theme-gui."""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk  # noqa: E402

from ..colors import hex_to_rgb, rgba_to_hex


class ColorButton(Gtk.Button):
    """A circular colour swatch button opening a colour chooser dialog.

    Uses GTK3's native ``Gtk.ColorChooserDialog``; the swatch itself is drawn
    with a small per-widget CSS provider (this GTK build has no Adwaita).
    """

    def __init__(self, hex_color: str = "#ffffff", **kwargs):
        super().__init__(**kwargs)
        self._color = hex_color
        self._provider = Gtk.CssProvider()
        self._apply_color(hex_color)
        self.get_style_context().add_provider(
            self._provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.get_style_context().add_class("color-swatch")
        self.set_size_request(30, 30)

    def _apply_color(self, hex_color: str):
        r, g, b = hex_to_rgb(hex_color)
        css = (
            f"button {{ background: rgba({r},{g},{b},1.0); "
            f"min-width: 26px; min-height: 26px; padding: 0; "
            f"border-radius: 50%; }}"
        )
        self._provider.load_from_data(css.encode())
        self.queue_draw()

    def get_color(self) -> str:
        return self._color

    def set_color(self, hex_color: str):
        self._color = hex_color
        self._apply_color(hex_color)

    def connect_color_changed(self, callback):
        def on_clicked(btn):
            parent = self.get_toplevel()
            dialog = Gtk.ColorChooserDialog(
                title="Pick a Colour",
                transient_for=parent if isinstance(parent, Gtk.Window) else None,
            )
            from gi.repository import Gdk

            rgba = Gdk.RGBA()
            rgba.parse(self._color)
            dialog.set_rgba(rgba)

            def on_response(dlg, response):
                if response == Gtk.ResponseType.OK:
                    chosen = dlg.get_rgba()
                    hex_val = rgba_to_hex(
                        chosen.red, chosen.green, chosen.blue, chosen.alpha
                    )
                    callback(self, hex_val)
                dlg.destroy()

            dialog.connect("response", on_response)
            dialog.show()

        self.connect("clicked", on_clicked)
