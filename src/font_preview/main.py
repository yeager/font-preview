#!/usr/bin/env python3
# Font Preview - A better font viewer for Linux
# Copyright (C) 2025 Daniel Nylander <daniel@danielnylander.se>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Main application entry point."""

import sys
import gi
import gettext
import locale
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio

# i18n
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "po")
if not os.path.isdir(LOCALE_DIR):
    LOCALE_DIR = "/usr/share/locale"
gettext.bindtextdomain("font-preview", LOCALE_DIR)
gettext.textdomain("font-preview")
_ = gettext.gettext

class FontPreviewApplication(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="se.danielnylander.FontPreview",
        GLib.set_application_name(_("Font Preview"))
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        export_action = Gio.SimpleAction.new("export", None)
        export_action.connect("activate", lambda *_: self.props.active_window and self.props.active_window._on_export_clicked())
        self.add_action(export_action)
        self.set_accels_for_action("app.export", ["<Control>e"])

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.refresh", ["F5"])
        self.set_accels_for_action("app.shortcuts", ["<Control>slash"])
        for n, cb in [("quit", lambda *_: self.quit()),
                      ("refresh", lambda *_: self._do_refresh()),
                      ("shortcuts", self._show_shortcuts_window)]:
            a = Gio.SimpleAction.new(n, None); a.connect("activate", cb); self.add_action(a)

    def _do_refresh(self):
        w = self.get_active_window()
        if w and hasattr(w, '_load_data'): w._load_data(force=True)
        elif w and hasattr(w, '_on_refresh'): w._on_refresh(None)

    def _show_shortcuts_window(self, *_args):
        win = Gtk.ShortcutsWindow(transient_for=self.get_active_window(), modal=True)
        section = Gtk.ShortcutsSection(visible=True, max_height=10)
        group = Gtk.ShortcutsGroup(visible=True, title="General")
        for accel, title in [("<Control>q", "Quit"), ("F5", "Refresh"), ("<Control>slash", "Keyboard shortcuts")]:
            s = Gtk.ShortcutsShortcut(visible=True, accelerator=accel, title=title)
            group.append(s)
        section.append(group)
        win.add_child(section)
        win.present()

    def do_activate(self):
        from .window import FontPreviewWindow

        win = self.props.active_window
        if not win:
            win = FontPreviewWindow(application=self)
        win.present()

    def _on_about(self, action, param):
        about = Adw.AboutDialog(
            application_name=_("Font Preview"),
            application_icon="font-preview",
            version="0.1.0",
            developer_name="Daniel Nylander",
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            copyright="© 2025 Daniel Nylander",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/yeager/font-preview",
            issue_url="https://github.com/yeager/font-preview/issues",
            comments=_("A localization tool by Daniel Nylander"),
            translator_credits=_("Translate this app: https://www.transifex.com/danielnylander/font-preview/"),
        )
        about.add_link(_("Help translate"), "https://app.transifex.com/danielnylander/font-preview/")

        about.present(self.props.active_window)

def main():
    """Application entry point."""
    app = FontPreviewApplication()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
