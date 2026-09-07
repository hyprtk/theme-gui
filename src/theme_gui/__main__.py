"""Entry point for theme-gui."""
import sys

import gi
gi.require_version("GLib", "2.0")

from gi.repository import GLib  # noqa: E402

from .app import ThemeGuiApp


def main():
    # GTK3 derives the Wayland app_id / WM_CLASS from the program name, so the
    # Hyprland windowrule (class = dev.hyprtk.theme_gui, float + size) matches.
    GLib.set_prgname("dev.hyprtk.theme_gui")
    app = ThemeGuiApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
