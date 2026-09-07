"""Color picker button with accessible labels and proper touch targets."""
from __future__ import annotations

from gi.repository import Gtk, Gdk

from ..colors import rgba_to_hex, hex_to_rgb


class ColorChooserWindow(Gtk.Window):
    """Custom color chooser dialog with full size control."""

    def __init__(self, parent, hex_color: str, callback):
        super().__init__(title="Pick a Colour")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(500, 450)
        self.set_resizable(True)
        self._callback = callback
        self._hex_color = hex_color

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_start(12)
        vbox.set_margin_end(12)

        self._chooser = Gtk.ColorChooserWidget()
        self._chooser.set_use_alpha(True)
        self._chooser.set_hexpand(True)
        self._chooser.set_vexpand(True)

        rgba = Gdk.RGBA()
        rgba.parse(hex_color)
        self._chooser.set_rgba(rgba)
        self._chooser.connect("color-activated", self._on_color_activated)
        vbox.append(self._chooser)

        self._hex_label = Gtk.Label(label=hex_color)
        self._hex_label.set_xalign(0)
        vbox.append(self._hex_label)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.destroy())
        btn_box.append(cancel_btn)

        select_btn = Gtk.Button(label="Select")
        select_btn.add_css_class("suggested-action")
        select_btn.connect("clicked", self._on_select)
        btn_box.append(select_btn)

        vbox.append(btn_box)
        self.set_child(vbox)

    def _on_color_activated(self, widget, rgba):
        self._hex_color = rgba_to_hex(rgba.red, rgba.green, rgba.blue, rgba.alpha)
        self._hex_label.set_text(self._hex_color)

    def _on_select(self, btn):
        rgba = self._chooser.get_rgba()
        hex_str = rgba_to_hex(rgba.red, rgba.green, rgba.blue, rgba.alpha)
        if self._callback:
            self._callback(self, hex_str)
        self.destroy()


class ColorButton(Gtk.Button):
    """A button that displays a color swatch using CSS background.

    Touch target is 44x44px minimum for accessibility.
    """

    def __init__(self, hex_color: str = "#ffffff", **kwargs):
        super().__init__(**kwargs)
        self._color = hex_color
        self._provider = Gtk.CssProvider()
        self._apply_color(hex_color)
        self.get_style_context().add_provider(
            self._provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )
        self.set_size_request(44, 44)

    def _apply_color(self, hex_color: str):
        r, g, b = hex_to_rgb(hex_color)
        h = hex_color.lstrip("#")
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        css = (
            f"button {{ background: rgba({r},{g},{b},{a:.2f}); "
            f"border-radius: 14px; min-width: 40px; min-height: 40px; padding: 0; }}"
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
            widget = self
            while widget is not None:
                if isinstance(widget, Gtk.ApplicationWindow):
                    break
                widget = widget.get_parent()
            parent = widget if widget else self.get_root()
            dialog = ColorChooserWindow(parent, self._color, callback)
            dialog.present()

        self.connect("clicked", on_clicked)
