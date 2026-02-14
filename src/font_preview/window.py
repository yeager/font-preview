#!/usr/bin/env python3
# Font Preview - A better font viewer for Linux
# Copyright (C) 2025 Daniel Nylander <daniel@danielnylander.se>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Main application window."""

import gettext
import json
import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")

from gi.repository import Gtk, Adw, Gio, GLib, Pango

from .font_utils import (
    FontInfo,
    get_installed_fonts,
    get_font_coverage,
    get_block_coverage,
    get_language_coverage,
    UNICODE_BLOCKS,
    LANGUAGE_CHARS,
)

_ = gettext.gettext

FAVORITES_FILE = os.path.expanduser("~/.config/font-preview/favorites.json")


def _load_favorites() -> set[str]:
    try:
        with open(FAVORITES_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_favorites(favs: set[str]):
    os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
    with open(FAVORITES_FILE, "w") as f:
        json.dump(sorted(favs), f)


class FontPreviewWindow(Adw.ApplicationWindow):
    """Main window."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title(_("Font Preview"))
        self.set_default_size(1100, 750)

        self._fonts: list[FontInfo] = []
        self._filtered_fonts: list[FontInfo] = []
        self._favorites: set[str] = _load_favorites()
        self._compare_fonts: list[FontInfo] = []
        self._preview_text = _("The quick brown fox jumps over the lazy dog. 0123456789")

        self._build_ui()
        self._load_fonts()

    def _build_ui(self):
        # Main layout: split view
        self._split = Adw.OverlaySplitView()
        self._split.set_collapsed(False)
        self._split.set_sidebar_position(Gtk.PackType.START)

        # --- Sidebar ---
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar for sidebar
        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_title_widget(Gtk.Label(label=_("Fonts")))
        sidebar_box.append(sidebar_header)

        # Search
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text(_("Search fonts…"))
        self._search_entry.set_margin_start(6)
        self._search_entry.set_margin_end(6)
        self._search_entry.set_margin_top(6)
        self._search_entry.set_margin_bottom(6)
        self._search_entry.connect("search-changed", self._on_search_changed)
        sidebar_box.append(self._search_entry)

        # Filter: All / Favorites
        self._filter_dropdown = Gtk.DropDown.new_from_strings([_("All Fonts"), _("Favorites")])
        self._filter_dropdown.set_margin_start(6)
        self._filter_dropdown.set_margin_end(6)
        self._filter_dropdown.set_margin_bottom(6)
        self._filter_dropdown.connect("notify::selected", self._on_filter_changed)
        sidebar_box.append(self._filter_dropdown)

        # Font list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._font_listbox = Gtk.ListBox()
        self._font_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._font_listbox.connect("row-selected", self._on_font_selected)
        scroll.set_child(self._font_listbox)
        sidebar_box.append(scroll)

        self._split.set_sidebar(sidebar_box)

        # --- Content ---
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar
        header = Adw.HeaderBar()
        self._title_label = Gtk.Label(label=_("Font Preview"))
        header.set_title_widget(self._title_label)

        # Compare button
        self._compare_btn = Gtk.ToggleButton(label=_("Compare"))
        self._compare_btn.connect("toggled", self._on_compare_toggled)
        header.pack_start(self._compare_btn)

        # Favorite button
        self._fav_btn = Gtk.Button(icon_name="starred-symbolic")
        self._fav_btn.set_tooltip_text(_("Toggle favorite"))
        self._fav_btn.connect("clicked", self._on_toggle_favorite)
        header.pack_end(self._fav_btn)

        content_box.append(header)

        # Preview text entry
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        entry_box.set_margin_start(12)
        entry_box.set_margin_end(12)
        entry_box.set_margin_top(12)
        lbl = Gtk.Label(label=_("Preview text:"))
        entry_box.append(lbl)
        self._preview_entry = Gtk.Entry()
        self._preview_entry.set_text(self._preview_text)
        self._preview_entry.set_hexpand(True)
        self._preview_entry.connect("changed", self._on_preview_text_changed)
        entry_box.append(self._preview_entry)
        content_box.append(entry_box)

        # Notebook for tabs
        self._notebook = Gtk.Notebook()
        self._notebook.set_margin_start(12)
        self._notebook.set_margin_end(12)
        self._notebook.set_margin_top(6)
        self._notebook.set_margin_bottom(12)
        self._notebook.set_vexpand(True)

        # Tab 1: Preview
        self._preview_scroll = Gtk.ScrolledWindow()
        self._preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._preview_box.set_margin_start(12)
        self._preview_box.set_margin_top(12)
        self._preview_box.set_margin_end(12)
        self._preview_box.set_margin_bottom(12)
        self._preview_scroll.set_child(self._preview_box)
        self._notebook.append_page(self._preview_scroll, Gtk.Label(label=_("Preview")))

        # Tab 2: Unicode Coverage
        self._coverage_scroll = Gtk.ScrolledWindow()
        self._coverage_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._coverage_box.set_margin_start(12)
        self._coverage_box.set_margin_top(12)
        self._coverage_box.set_margin_end(12)
        self._coverage_box.set_margin_bottom(12)
        self._coverage_scroll.set_child(self._coverage_box)
        self._notebook.append_page(self._coverage_scroll, Gtk.Label(label=_("Unicode Coverage")))

        # Tab 3: Language Coverage
        self._lang_scroll = Gtk.ScrolledWindow()
        self._lang_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._lang_box.set_margin_start(12)
        self._lang_box.set_margin_top(12)
        self._lang_box.set_margin_end(12)
        self._lang_box.set_margin_bottom(12)
        self._lang_scroll.set_child(self._lang_box)
        self._notebook.append_page(self._lang_scroll, Gtk.Label(label=_("Language Coverage")))

        # Tab 4: Metadata
        self._meta_scroll = Gtk.ScrolledWindow()
        self._meta_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._meta_box.set_margin_start(12)
        self._meta_box.set_margin_top(12)
        self._meta_box.set_margin_end(12)
        self._meta_box.set_margin_bottom(12)
        self._meta_scroll.set_child(self._meta_box)
        self._notebook.append_page(self._meta_scroll, Gtk.Label(label=_("Metadata")))

        # Tab 5: Compare
        self._compare_scroll = Gtk.ScrolledWindow()
        self._compare_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._compare_box.set_margin_start(12)
        self._compare_box.set_margin_top(12)
        self._compare_box.set_margin_end(12)
        self._compare_box.set_margin_bottom(12)
        self._compare_scroll.set_child(self._compare_box)
        self._notebook.append_page(self._compare_scroll, Gtk.Label(label=_("Compare")))

        content_box.append(self._notebook)
        self._split.set_content(content_box)

        # Wrap in toolbar view
        self.set_content(self._split)

    def _load_fonts(self):
        """Load fonts in background thread."""
        def _do_load():
            fonts = get_installed_fonts()
            for f in fonts:
                f.favorite = f.family in self._favorites
            GLib.idle_add(self._fonts_loaded, fonts)

        threading.Thread(target=_do_load, daemon=True).start()

    def _fonts_loaded(self, fonts: list[FontInfo]):
        self._fonts = fonts
        self._apply_filter()

    def _apply_filter(self):
        query = self._search_entry.get_text().lower().strip()
        show_favs = self._filter_dropdown.get_selected() == 1

        self._filtered_fonts = []
        for f in self._fonts:
            if show_favs and not f.favorite:
                continue
            if query and query not in f.family.lower() and query not in f.style.lower():
                continue
            self._filtered_fonts.append(f)

        self._populate_list()

    def _populate_list(self):
        # Clear
        while True:
            row = self._font_listbox.get_row_at_index(0)
            if row is None:
                break
            self._font_listbox.remove(row)

        for font in self._filtered_fonts:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box.set_margin_start(6)
            box.set_margin_end(6)
            box.set_margin_top(3)
            box.set_margin_bottom(3)

            if font.favorite:
                star = Gtk.Image.new_from_icon_name("starred-symbolic")
                box.append(star)

            label = Gtk.Label(label=font.display_name, xalign=0)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_hexpand(True)
            box.append(label)

            row.set_child(box)
            row._font_info = font
            self._font_listbox.append(row)

    def _on_search_changed(self, entry):
        self._apply_filter()

    def _on_filter_changed(self, dropdown, _pspec):
        self._apply_filter()

    def _on_font_selected(self, listbox, row):
        if row is None:
            return
        font = row._font_info
        self._title_label.set_label(font.display_name)

        if self._compare_btn.get_active():
            if len(self._compare_fonts) >= 4:
                self._compare_fonts.pop(0)
            # Avoid duplicates
            if not any(f.path == font.path for f in self._compare_fonts):
                self._compare_fonts.append(font)
            self._update_compare()
            self._notebook.set_current_page(4)
        else:
            self._update_preview(font)
            self._update_coverage(font)
            self._update_lang_coverage(font)
            self._update_metadata(font)

    def _on_preview_text_changed(self, entry):
        self._preview_text = entry.get_text()
        row = self._font_listbox.get_selected_row()
        if row:
            self._update_preview(row._font_info)
        if self._compare_fonts:
            self._update_compare()

    def _on_toggle_favorite(self, btn):
        row = self._font_listbox.get_selected_row()
        if not row:
            return
        font = row._font_info
        if font.family in self._favorites:
            self._favorites.discard(font.family)
            font.favorite = False
        else:
            self._favorites.add(font.family)
            font.favorite = True
        _save_favorites(self._favorites)
        # Mark all fonts with same family
        for f in self._fonts:
            f.favorite = f.family in self._favorites
        self._apply_filter()

    def _on_compare_toggled(self, btn):
        if not btn.get_active():
            self._compare_fonts.clear()
            self._clear_box(self._compare_box)

    def _clear_box(self, box):
        while True:
            child = box.get_first_child()
            if child is None:
                break
            box.remove(child)

    def _update_preview(self, font: FontInfo):
        self._clear_box(self._preview_box)

        sizes = [12, 18, 24, 36, 48, 72]
        for size in sizes:
            label = Gtk.Label(xalign=0, wrap=True)
            label.set_markup(
                f'<span font_desc="{GLib.markup_escape_text(font.family)} {size}">'
                f'{GLib.markup_escape_text(self._preview_text)}</span>'
            )
            size_lbl = Gtk.Label(label=f"{size}px", xalign=0)
            size_lbl.add_css_class("dim-label")
            self._preview_box.append(size_lbl)
            self._preview_box.append(label)
            self._preview_box.append(Gtk.Separator())

    def _update_coverage(self, font: FontInfo):
        self._clear_box(self._coverage_box)

        title = Gtk.Label(label=_("Unicode Block Coverage"), xalign=0)
        title.add_css_class("title-3")
        self._coverage_box.append(title)

        def _load_coverage():
            supported = get_font_coverage(font.path)
            GLib.idle_add(_show_coverage, supported)

        def _show_coverage(supported):
            # Remove spinner if any
            self._clear_box(self._coverage_box)
            title2 = Gtk.Label(label=_("Unicode Block Coverage"), xalign=0)
            title2.add_css_class("title-3")
            self._coverage_box.append(title2)

            total_label = Gtk.Label(
                label=_("Total glyphs: %d") % len(supported), xalign=0
            )
            self._coverage_box.append(total_label)
            self._coverage_box.append(Gtk.Separator())

            for block_name, (start, end) in sorted(UNICODE_BLOCKS.items()):
                pct = get_block_coverage(supported, start, end)
                if pct == 0:
                    continue
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                name_label = Gtk.Label(label=block_name, xalign=0)
                name_label.set_hexpand(True)
                name_label.set_size_request(200, -1)
                row.append(name_label)

                bar = Gtk.ProgressBar()
                bar.set_fraction(pct / 100)
                bar.set_hexpand(True)
                bar.set_valign(Gtk.Align.CENTER)
                row.append(bar)

                pct_label = Gtk.Label(label=f"{pct:.0f}%", xalign=1)
                pct_label.set_size_request(50, -1)
                row.append(pct_label)

                self._coverage_box.append(row)

        spinner = Gtk.Spinner()
        spinner.start()
        self._coverage_box.append(spinner)
        threading.Thread(target=_load_coverage, daemon=True).start()

    def _update_lang_coverage(self, font: FontInfo):
        self._clear_box(self._lang_box)

        title = Gtk.Label(label=_("Language Coverage"), xalign=0)
        title.add_css_class("title-3")
        self._lang_box.append(title)

        def _load():
            supported = get_font_coverage(font.path)
            GLib.idle_add(_show, supported)

        def _show(supported):
            self._clear_box(self._lang_box)
            title2 = Gtk.Label(label=_("Language Coverage"), xalign=0)
            title2.add_css_class("title-3")
            self._lang_box.append(title2)

            for lang in sorted(LANGUAGE_CHARS.keys()):
                pct, missing = get_language_coverage(supported, lang)
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

                name_label = Gtk.Label(label=lang, xalign=0)
                name_label.set_hexpand(True)
                name_label.set_size_request(180, -1)
                row.append(name_label)

                bar = Gtk.ProgressBar()
                bar.set_fraction(pct / 100)
                bar.set_hexpand(True)
                bar.set_valign(Gtk.Align.CENTER)
                row.append(bar)

                pct_label = Gtk.Label(label=f"{pct:.0f}%", xalign=1)
                pct_label.set_size_request(50, -1)
                row.append(pct_label)

                self._lang_box.append(row)

                if missing and len(missing) <= 20:
                    miss_str = " ".join(missing)
                    miss_label = Gtk.Label(
                        label=_("Missing: %s") % miss_str, xalign=0
                    )
                    miss_label.add_css_class("dim-label")
                    miss_label.set_margin_start(12)
                    self._lang_box.append(miss_label)

        spinner = Gtk.Spinner()
        spinner.start()
        self._lang_box.append(spinner)
        threading.Thread(target=_load, daemon=True).start()

    def _update_metadata(self, font: FontInfo):
        self._clear_box(self._meta_box)

        title = Gtk.Label(label=_("Font Metadata"), xalign=0)
        title.add_css_class("title-3")
        self._meta_box.append(title)

        fields = [
            (_("Family"), font.family),
            (_("Style"), font.style),
            (_("Weight"), font.weight),
            (_("Slant"), font.slant),
            (_("Width"), font.width),
            (_("File"), font.path),
        ]

        for label_text, value in fields:
            if not value:
                continue
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            key = Gtk.Label(label=f"<b>{GLib.markup_escape_text(label_text)}:</b>", use_markup=True, xalign=0)
            key.set_size_request(100, -1)
            row.append(key)
            val = Gtk.Label(label=value, xalign=0, selectable=True, wrap=True)
            val.set_hexpand(True)
            row.append(val)
            self._meta_box.append(row)

    def _update_compare(self):
        self._clear_box(self._compare_box)

        if not self._compare_fonts:
            lbl = Gtk.Label(label=_("Select 2–4 fonts to compare"))
            self._compare_box.append(lbl)
            return

        info = Gtk.Label(
            label=_("Comparing %d fonts (click more to add, max 4)") % len(self._compare_fonts),
            xalign=0,
        )
        info.add_css_class("dim-label")
        self._compare_box.append(info)

        # Clear button
        clear_btn = Gtk.Button(label=_("Clear comparison"))
        clear_btn.connect("clicked", lambda b: (self._compare_fonts.clear(), self._update_compare()))
        self._compare_box.append(clear_btn)

        self._compare_box.append(Gtk.Separator())

        for font in self._compare_fonts:
            frame = Gtk.Frame()
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            vbox.set_margin_start(12)
            vbox.set_margin_end(12)
            vbox.set_margin_top(6)
            vbox.set_margin_bottom(6)

            name = Gtk.Label(label=font.display_name, xalign=0)
            name.add_css_class("title-4")
            vbox.append(name)

            preview = Gtk.Label(xalign=0, wrap=True)
            preview.set_markup(
                f'<span font_desc="{GLib.markup_escape_text(font.family)} 24">'
                f'{GLib.markup_escape_text(self._preview_text)}</span>'
            )
            vbox.append(preview)

            frame.set_child(vbox)
            self._compare_box.append(frame)
