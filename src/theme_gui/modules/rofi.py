"""Rofi theme variant manager (GTK3)."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")

from gi.repository import Gtk, Pango  # noqa: E402

from .. import paths  # noqa: E402
from ..widgets import BasePage, remove_all_children, show_toast  # noqa: E402

log = logging.getLogger(__name__)


class RofiPage(BasePage):
    def __init__(self, **kwargs):
        super().__init__(title="Rofi Themes", **kwargs)

        self._active_label = Gtk.Label(label="Active variant: ...", xalign=0)
        self._active_label.get_style_context().add_class("heading")
        self.body.pack_start(self._active_label, False, False, 0)

        list_sec = self.section("Variants")
        self._variant_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        list_sec.pack_start(self._variant_list, False, False, 0)

        apply_btn = self.flat_button("Regenerate from Pywal")
        apply_btn.connect("clicked", self._regenerate)
        self.body.pack_start(apply_btn, False, False, 0)

        self._refresh()

    def on_shown(self):
        self._refresh()

    def _refresh(self):
        self._load_active()
        self._load_variants()

    def _load_active(self):
        link = paths.ROFI_VARIANT_LINK
        if link.is_symlink():
            name = Path(os.readlink(str(link))).stem
            self._active_label.set_text(f"Active variant: {name}")
        else:
            self._active_label.set_text("Active variant: (none)")

    def _load_variants(self):
        remove_all_children(self._variant_list)
        variants_dir = paths.ROFI_VARIANTS
        if not variants_dir.exists():
            return
        link = paths.ROFI_VARIANT_LINK
        active_target = (
            os.readlink(str(link)) if link.is_symlink() else None
        )
        for f in sorted(variants_dir.glob("*.rasi")):
            row = Gtk.Button()
            row.get_style_context().add_class("flat")
            row.get_style_context().add_class("tg-row")
            row.set_halign(Gtk.Align.FILL)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=f.stem, xalign=0)
            lbl.set_hexpand(True)
            box.pack_start(lbl, True, True, 0)
            if active_target == str(f):
                badge = Gtk.Label(label="Active")
                badge.get_style_context().add_class("badge")
                box.pack_start(badge, False, False, 0)
                row.get_style_context().add_class("active")
            row.add(box)
            row.connect("clicked", self._on_variant_click, f)
            self._variant_list.pack_start(row, False, False, 0)
        self._variant_list.show_all()

    def _on_variant_click(self, _btn, variant_path: Path):
        link = paths.ROFI_VARIANT_LINK
        link.unlink(missing_ok=True)
        os.symlink(str(variant_path), str(link))
        self._run_script(paths.SYNC_ROFI_SH, "rofi sync")
        self._refresh()
        show_toast(self, f"Rofi variant: {variant_path.stem}")

    def _regenerate(self, btn):
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
