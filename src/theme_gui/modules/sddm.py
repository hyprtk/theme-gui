"""SDDM & GRUB wallpaper updater module (GTK3)."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import GdkPixbuf, Gtk  # noqa: E402

from .. import paths  # noqa: E402
from ..widgets import BasePage, show_toast  # noqa: E402

log = logging.getLogger(__name__)

UPDATE_SH = Path.home() / "hyprtk" / "configs" / "sddm" / "update.sh"


class SddmPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="SDDM & GRUB", **kwargs)

        info = Gtk.Label(
            label="Update the login screen (SDDM) and bootloader (GRUB) "
            "with your current wallpaper.",
            xalign=0,
            wrap=True,
        )
        info.get_style_context().add_class("dim-label")
        self.body.pack_start(info, False, False, 0)

        self._wallpaper_path = Path.home() / ".cache" / "current-wallpaper.png"
        if self._wallpaper_path.exists():
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(self._wallpaper_path), -1, 200, True
                )
                img = Gtk.Image.new_from_pixbuf(pb)
                img.set_halign(Gtk.Align.FILL)
                img.get_style_context().add_class("preview-frame")
                self.body.pack_start(img, False, False, 0)
            except Exception:
                pass

        update_btn = self.primary_button("Update SDDM & GRUB Wallpaper")
        update_btn.set_margin_top(8)
        update_btn.connect("clicked", self._on_update)
        self.body.pack_start(update_btn, False, False, 0)
        self._update_btn = update_btn

        self._status = Gtk.Label(label="", xalign=0)
        self._status.get_style_context().add_class("dim-label")
        self.body.pack_start(self._status, False, False, 0)

    def _on_update(self, btn):
        if not UPDATE_SH.is_file():
            show_toast(self, "update.sh not found", timeout=4)
            return
        if not self._wallpaper_path.exists():
            show_toast(self, "No current wallpaper found", timeout=4)
            return

        self._status.set_text("Updating SDDM & GRUB...")
        btn.set_sensitive(False)

        try:
            proc = subprocess.run(
                ["pkexec", "env", f"HOME={Path.home()}", "bash", str(UPDATE_SH), "-y"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode == 0:
                self._status.set_text("Done! Reboot to test.")
                show_toast(self, "SDDM & GRUB updated", timeout=4)
            else:
                self._status.set_text(f"Error: {proc.stderr[:200]}")
                show_toast(self, "Update failed", timeout=4)
        except subprocess.TimeoutExpired:
            self._status.set_text("Update timed out")
            show_toast(self, "Update timed out", timeout=4)
        except Exception as exc:
            log.warning("SDDM/GRUB update failed: %s", exc)
            self._status.set_text(f"Error: {exc}")
            show_toast(self, "Update failed", timeout=4)
        finally:
            btn.set_sensitive(True)
