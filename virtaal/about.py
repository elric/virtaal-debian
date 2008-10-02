#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import os
import __version__
from support import openmailto
import pan_app


class About(gtk.AboutDialog):
    def __init__(self, parent):
        gtk.AboutDialog.__init__(self)
        self._register_uri_handlers()
        self.set_name("Virtaal")
        self.set_version(__version__.ver)
        self.set_copyright(_(u"© Copyright 2007-2008 Zuza Software Foundation"))
        self.set_comments(_("Advanced Computer Aided Translation (CAT) tool for localization and translation"))
        self.set_license("""This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Library General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.""")
        self.set_website("http://translate.sourceforge.net/wiki/virtaal/index")
        self.set_website_label(_("Virtaal website"))
        self.set_authors([
                "Friedel Wolff <friedel@translate.org.za>",
                "Wynand Winterbach <wynand@translate.org.za>",
                "Dwayne Bailey <dwayne@translate.org.za>",
                "Walter Leibbrandt <walter@translate.org.za>",
                ])
        self.set_translator_credits(_("translator-credits"))
        self.set_icon(parent.get_icon())
        self.set_logo(gtk.gdk.pixbuf_new_from_file(pan_app.get_abs_data_filename(["virtaal", "virtaal_logo.png"])))
        self.set_artists([
                "Heather Bailey <heather@translate.org.za>",
                ])
        # FIXME entries that we may want to add
        #self.set_documenters()
        self.connect ("response", lambda d, r: d.destroy())
        self.show()

    def on_url(self, dialog, uri, data):
        if data == "mail":
            openmailto.mailto(uri)
        elif data == "url":
            openmailto.open(uri)

    def _register_uri_handlers(self):
        """Register the URL and email handlers

        Use open and mailto from virtaal.support.openmailto
        """
        gtk.about_dialog_set_url_hook(self.on_url, "url")
        gtk.about_dialog_set_email_hook(self.on_url, "mail")
