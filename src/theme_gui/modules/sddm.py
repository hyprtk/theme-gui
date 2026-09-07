"""SDDM & GRUB wallpaper updater module."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from gi.repository import Adw, Gtk

from .. import paths
from ..widgets import BasePage, show_toast

log = logging.getLogger(__name__)

UPDATE_SH = Path.home() / "hyprtk" / "configs" / "sddm" / "update.sh"


class SddmPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="SDDM & GRUB", **kwargs)

        # info label
        info = Gtk.Label(
            label="Update the login screen (SDDM) and bootloader (GRUB)\n"
                  "with your current wallpaper.",
        )
        info.set_xalign(0)
        info.set_wrap(True)
        info.add_css_class("dim-label")
        self._box.append(info)

        # current wallpaper preview
        self._wallpaper_path = Path.home() / ".cache" / "current-wallpaper.png"
        if self._wallpaper_path.exists():
            img = Gtk.Picture()
            img.set_filename(str(self._wallpaper_path))
            img.set_content_fit(Gtk.ContentFit.CONTAIN)
            img.set_size_request(-1, 200)
            img.add_css_class("card")
            self._box.append(img)

        # update button
        update_btn = Gtk.Button(label="Update SDDM & GRUB Wallpaper")
        update_btn.add_css_class("suggested-action")
        update_btn.set_margin_top(12)
        update_btn.connect("clicked", self._on_update)
        self._box.append(update_btn)

        # status
        self._status = Gtk.Label(label="")
        self._status.set_xalign(0)
        self._box.append(self._status)

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
