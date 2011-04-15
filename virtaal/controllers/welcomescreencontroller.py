#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2011 Zuza Software Foundation
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


from basecontroller import BaseController


class WelcomeScreenController(BaseController):
    """
    Contains logic for the welcome screen.
    """

    MAX_RECENT = 5
    """The maximum number of recent items to display."""

    LINKS = {
        'manual':   _('http://translate.sourceforge.net/wiki/virtaal/using_virtaal'),
        'locguide': _('http://translate.sourceforge.net/wiki/guide/start'),
        # FIXME: The URL below should be replaced with a proper feedback URL
        'feedback': _("http://translate.sourceforge.net/wiki/virtaal/index#contact"),
        'features_more': _('http://translate.sourceforge.net/wiki/virtaal/features')
    }

    # INITIALIZERS #
    def __init__(self, main_controller):
        self.main_controller = main_controller
        main_controller.welcomescreen_controller = self

        self._recent_files = []
        from virtaal.views.welcomescreenview import WelcomeScreenView
        self.view = WelcomeScreenView(self)

        main_controller.store_controller.connect('store-closed', self._on_store_closed)
        main_controller.store_controller.connect('store-loaded', self._on_store_loaded)


    # METHODS #
    def activate(self):
        """Show the welcome screen and trigger activation logic (ie. find
            recent files)."""
        self.update_recent()
        self.view.show()

    def open_cheatsheat(self):
        from virtaal.support import openmailto
        # FIXME: The URL below is just a temporary solution
        openmailto.open(_('http://translate.sourceforge.net/wiki/virtaal/cheatsheet'))

    def open_file(self, filename=None):
        self.main_controller.open_file(filename)

    def open_recent(self, n):
        n -= 1 # Shift from nominal value [1; 5] to index value [0; 4]
        if 0 <= n <= len(self._recent_files)-1:
            self.open_file(self._recent_files[n]['uri'].decode('utf-8'))
        else:
            import logging
            logging.debug('Invalid recent file index (%d) given. Recent files: %s)' % (n, self._recent_files))

    def open_tutorial(self):
        self.main_controller.open_tutorial()

    def try_open_link(self, name):
        if name not in self.LINKS:
            return False
        from virtaal.support import openmailto
        openmailto.open(self.LINKS[name])
        return True

    def update_recent(self):
        from virtaal.views import recent
        self._recent_files = [{
                'name': i.get_display_name(),
                'uri':  i.get_uri_display()
            } for i in recent.rc.get_items()[:self.MAX_RECENT]
        ]
        self.view.update_recent_buttons(self._recent_files)


    # EVENT HANDLERS #
    def _on_store_closed(self, store_controller):
        self.activate()

    def _on_store_loaded(self, store_controller):
        self.view.hide()
