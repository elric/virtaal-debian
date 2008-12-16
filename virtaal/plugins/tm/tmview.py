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
import gobject
import logging
from gtk import gdk

from virtaal.common import GObjectWrapper
from virtaal.views import BaseView

from tmwidgets import *


class TMView(BaseView, GObjectWrapper):
    """The fake drop-down menu in which the TM matches are displayed."""

    __gtype_name__ = 'TMView'
    __gsignals__ = {
        'tm-match-selected': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    # INITIALIZERS #
    def __init__(self, controller):
        GObjectWrapper.__init__(self)

        self.controller = controller
        self.isvisible = False
        self._may_show_tmwindow = False
        self._should_show_tmwindow = False

        self.tmwindow = TMWindow(self)
        self.tmwindow.treeview.connect('row-activated', self._on_row_activated)

        main_window = self.controller.main_controller.view.main_window
        main_window.connect('focus-in-event', self._on_focus_in_mainwindow)
        main_window.connect('focus-out-event', self._on_focus_out_mainwindow)
        self._setup_key_bindings()

    def _setup_key_bindings(self):
        """Setup Gtk+ key bindings (accelerators)."""
        gtk.accel_map_add_entry("<Virtaal>/TM/Hide TM", gtk.keysyms.Escape, 0)
        gtk.accel_map_add_entry("<Virtaal>/TM/Select match 1", gtk.keysyms._1, gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/TM/Select match 2", gtk.keysyms._2, gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/TM/Select match 3", gtk.keysyms._3, gdk.CONTROL_MASK)

        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_by_path("<Virtaal>/TM/Hide TM", self._on_hide_tm)
        self.accel_group.connect_by_path("<Virtaal>/TM/Select match 1", self._on_select_match)
        self.accel_group.connect_by_path("<Virtaal>/TM/Select match 2", self._on_select_match)
        self.accel_group.connect_by_path("<Virtaal>/TM/Select match 3", self._on_select_match)

        mainview = self.controller.main_controller.view
        mainview.add_accel_group(self.accel_group)


    # METHODS #
    def clear(self):
        self.tmwindow.liststore.clear()
        self.hide()

    def display_matches(self, matches):
        liststore = self.tmwindow.liststore

        for match in matches:
            tooltip = ''
            if len(liststore) < 3:
                tooltip = _('Ctrl+%(numeral)d') % {"numeral": len(liststore)+1}
            liststore.append([match, tooltip])

        if len(liststore) > 0:
            self.show()
            selected = self.controller.main_controller.unit_controller.view.targets[0]
            self.tmwindow.update_geometry(selected)

    def hide(self):
        """Hide the TM window."""
        self.tmwindow.hide()
        self.isvisible = False

    def select_match(self, match_data):
        """Select the match data as accepted by the user."""
        self.controller.select_match(match_data)

    def select_match_index(self, index):
        """Select the TM match with the given index (first match is C{1})."""
        if index < 0:
            return

        logging.debug('Selecting index %d' % (index))
        liststore = self.tmwindow.liststore
        itr = liststore.get_iter_first()

        i=1
        while i < index and liststore.iter_is_valid(itr):
            itr = liststore.iter_next(itr)
            i += 1

        if not itr or not liststore.iter_is_valid(itr):
            return

        path = liststore.get_path(itr)
        self.tmwindow.treeview.get_selection().select_iter(itr)
        self.tmwindow.treeview.row_activated(path, self.tmwindow.tvc_match)

    def show(self, force=False):
        """Show the TM window."""
        if (self.isvisible and not force) or not self._may_show_tmwindow:
            return # This window is already visible
        self.tmwindow.show_all()
        self.isvisible = True
        self._should_show_tmwindow = False


    # EVENT HANDLERS #
    def _on_focus_in_mainwindow(self, widget, event):
        self._may_show_tmwindow = True
        if not self._should_show_tmwindow or self.isvisible:
            return
        self.show()

        selected = self.controller.main_controller.unit_controller.view.targets[0]
        self.tmwindow.update_geometry(selected)

    def _on_focus_out_mainwindow(self, widget, event):
        self._may_show_tmwindow = False
        if not self.isvisible:
            return
        self.hide()
        self._should_show_tmwindow = True

    def _on_hide_tm(self, accel_group, acceleratable, keyval, modifier):
        self.hide()

    def _on_row_activated(self, treeview, path, column):
        """Called when a TM match is selected in the TM window."""
        liststore = treeview.get_model()
        assert liststore is self.tmwindow.liststore
        itr = liststore.get_iter(path)
        match_data = liststore.get_value(itr, 0)

        self.select_match(match_data)

    def _on_select_match(self, accel_group, acceleratable, keyval, modifier):
        self.select_match_index(int(keyval - gtk.keysyms._0))
