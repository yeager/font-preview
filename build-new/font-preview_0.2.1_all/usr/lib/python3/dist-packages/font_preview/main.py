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
gettext.bindtextdomain("font-preview", LOCALE_DIR)
gettext.textdomain("font-preview")
_ = gettext.gettext


class FontPreviewApplication(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="se.danielnylander.FontPreview",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def do_activate(self):
        from .window import FontPreviewWindow

        win = self.props.active_window
        if not win:
            win = FontPreviewWindow(application=self)
        win.present()

    def _on_about(self, action, param):
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
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
            translator_credits=_("Translate this app: https://app.transifex.com/danielnylander/font-preview/"),
        )
        about.present()


def main():
    """Application entry point."""
    app = FontPreviewApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
