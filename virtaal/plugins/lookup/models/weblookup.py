#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
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
import urllib
from os import path

from virtaal.common import pan_app

from baselookupmodel import BaseLookupModel


class LookupModel(BaseLookupModel):
    """Look-up the selected string on the web."""

    __gtype_name__ = 'WebLookupModel'
    display_name = _('Web Look-up')
    description = _('Use the selected text as the query string in a web look-ups.')

    URLDATA = (
        {
            'display_name': _('Google'),
            'url': 'http://www.google.com/search?q=%(query)s',
            'quoted': True,
        },
        {
            'display_name': _('WikiPedia'),
            'url': 'http://%(querylang)s.wikipedia.org/%(query)s',
            'quoted': False,
        },
    )

    # INITIALIZERS #
    def __init__(self, internal_name, controller):
        self.controller = controller
        self.internal_name = internal_name

        self.urldata_file = path.join(pan_app.get_config_dir(), "weblookup.ini")

        self._load_urldata()

    def _load_urldata(self):
        urls = pan_app.load_config(self.urldata_file).values()
        if urls:
            self.URLDATA = urls


    # METHODS #
    def create_menu_items(self, query, role, srclang, tgtlang):
        querylang = role == 'source' and srclang or tgtlang
        query = urllib.quote(query)
        items = []
        for urlinfo in self.URLDATA:
            uquery = query
            if 'quoted' in urlinfo and urlinfo['quoted']:
                uquery = '"' + uquery + '"'

            i = gtk.MenuItem(urlinfo['name'])
            lookup_str = urlinfo['url'] % {
                'query':     uquery,
                'querylang': querylang,
                'role':      role,
                'srclang':   srclang,
                'tgtlang':   tgtlang
            }
            i.connect('activate', self._on_lookup, lookup_str)
            items.append(i)
        return items

    def destroy(self):
        config = dict([ (u['display_name'], u) for u in self.URLDATA ])
        pan_app.save_config(self.urldata_file, config)


    # SIGNAL HANDLERS #
    def _on_lookup(self, menuitem, url):
        from virtaal.support.openmailto import open
        open(url)
