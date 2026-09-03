"""Rofi theme variant manager."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from gi.repository import Adw, Gtk

from .. import paths
from ..widgets import BasePage, remove_all_children, show_toast

log = logging.getLogger(__name__)


class RofiPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Rofi Themes", **kwargs)

        # active variant indicator
        self._active_label = Gtk.Label(label="Active variant: ...")
        self._active_label.set_xalign(0)
        self._active_label.add_css_class("heading")
        self._box.append(self._active_label)

        # variant list
        self._variant_list = Gtk.ListBox()
        self._variant_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._box.append(self._variant_list)

        # regenerate button
        apply_btn = Gtk.Button(label="Regenerate from Pywal")
        apply_btn.add_css_class("flat")
        apply_btn.connect("clicked", self._sync_to_waybar)
        self._box.append(apply_btn)

        self._refresh()
        self.connect("map", lambda w: self._refresh())

    def _refresh(self):
        self._load_active()
        self._load_variants()

    def _load_active(self):
        link = paths.ROFI_VARIANT_LINK
        if link.is_symlink():
            target = os.readlink(str(link))
            name = Path(target).stem
            self._active_label.set_text(f"Active variant: {name}")
        else:
            self._active_label.set_text("Active variant: (none)")

    def _load_variants(self):
        remove_all_children(self._variant_list)

        variants_dir = paths.ROFI_VARIANTS
        if not variants_dir.exists():
            return

        for f in sorted(variants_dir.glob("*.rasi")):
            row = Adw.ActionRow(title=f.stem)
            row.set_activatable(True)
            row.add_css_class("sidebar-row")
            row._variant_path = f

            link = paths.ROFI_VARIANT_LINK
            if link.is_symlink() and os.readlink(str(link)) == str(f):
                badge = Gtk.Label(label="Active")
                badge.add_css_class("success")
                row.add_suffix(badge)

            row.connect("activated", self._on_variant_click)
            self._variant_list.append(row)

    def _on_variant_click(self, row):
        variant_path = row._variant_path
        link = paths.ROFI_VARIANT_LINK
        link.unlink(missing_ok=True)
        os.symlink(str(variant_path), str(link))

        self._run_script(paths.SYNC_ROFI_SH, "rofi sync")
        self._refresh()
        show_toast(self, f"Rofi variant: {variant_path.stem}")

    def _sync_to_waybar(self, btn):
        self._run_script(paths.SYNC_ROFI_SH, "rofi sync")
        self._refresh()
        show_toast(self, "Regenerated rofi variant from pywal")

    def _run_script(self, script_path, label: str):
        if not script_path.is_file():
            show_toast(self, f"{label} script not found", timeout=4)
            return
        try:
            subprocess.Popen(["bash", str(script_path)], start_new_session=True)
        except FileNotFoundError as exc:
            log.warning("%s failed: %s", label, exc)
            show_toast(self, f"Failed to run {label}", timeout=4)
