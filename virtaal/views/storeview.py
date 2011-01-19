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

import gtk

from baseview import BaseView
from widgets.storetreeview import StoreTreeView


# XXX: ASSUMPTION: The model to display is self.controller.store
# TODO: Add event handler for store controller's cursor-creation event, so that
#       the store view can connect to the new cursor's "cursor-changed" event
#       (which is currently done in load_store())
class StoreView(BaseView):
    """The view of the store and interface to store-level actions."""

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        # XXX: While I can't think of a better way to do this, the following line would have to do :/
        self.parent_widget = self.controller.main_controller.view.gui.get_widget('scrwnd_storeview')

        self.cursor = None
        self._cursor_changed_id = 0

        self._init_treeview()
        self._add_accelerator_bindings()

        main_window = self.controller.main_controller.view.main_window
        main_window.connect('configure-event', self._treeview.on_configure_event)
        if main_window.get_property('visible'):
            # Because StoreView might be loaded lazily, the window might already
            # have its style set
            self._on_style_set(main_window, None)
        main_window.connect('style-set', self._on_style_set)

    def _init_treeview(self):
        self._treeview = StoreTreeView(self)

    def _add_accelerator_bindings(self):
        gtk.accel_map_add_entry("<Virtaal>/Navigation/Up", gtk.accelerator_parse("Up")[0], gtk.gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Navigation/Down", gtk.accelerator_parse("Down")[0], gtk.gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Navigation/PgUp", gtk.accelerator_parse("Page_Up")[0], gtk.gdk.CONTROL_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Navigation/PgDown", gtk.accelerator_parse("Page_Down")[0], gtk.gdk.CONTROL_MASK)

        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_by_path("<Virtaal>/Navigation/Up", self._treeview._move_up)
        self.accel_group.connect_by_path("<Virtaal>/Navigation/Down", self._treeview._move_down)
        self.accel_group.connect_by_path("<Virtaal>/Navigation/PgUp", self._treeview._move_pgup)
        self.accel_group.connect_by_path("<Virtaal>/Navigation/PgDown", self._treeview._move_pgdown)

        mainview = self.controller.main_controller.view
        mainview.add_accel_group(self.accel_group)
        mainview.gui.get_widget('menu_navigation').set_accel_group(self.accel_group)
        self.mnu_up = mainview.gui.get_widget('mnu_up')
        self.mnu_down = mainview.gui.get_widget('mnu_down')
        self.mnu_pageup = mainview.gui.get_widget('mnu_pageup')
        self.mnu_pagedown = mainview.gui.get_widget('mnu_pagedown')
        self.mnu_up.set_accel_path('<Virtaal>/Navigation/Up')
        self.mnu_down.set_accel_path('<Virtaal>/Navigation/Down')
        self.mnu_pageup.set_accel_path('<Virtaal>/Navigation/PgUp')
        self.mnu_pagedown.set_accel_path('<Virtaal>/Navigation/PgDown')

        self._set_menu_items_sensitive(False)


    # ACCESSORS #
    def get_store(self):
        return self.store

    def get_unit_celleditor(self, unit):
        return self.controller.get_unit_celleditor(unit)


    # METHODS #
    def hide(self):
        self.parent_widget.props.visible = False
        self.load_store(None)

    def load_store(self, store):
        self.store = store
        if store:
            self._treeview.set_model(store)
            self._set_menu_items_sensitive(True)
            self.cursor = self.controller.cursor
            self._cursor_changed_id = self.cursor.connect('cursor-changed', self._on_cursor_change)
        else:
            if self._cursor_changed_id and self.cursor:
                self.cursor.disconnect(self._cursor_changed_id)
                self.cursor = None
            self._set_menu_items_sensitive(False)
            self._treeview.set_model(None)

    def show(self):
        child = self.parent_widget.get_child()
        if child and child is not self._treeview:
            self.parent_widget.remove(child)
            child.destroy()
        if not self._treeview.parent:
            self.parent_widget.add(self._treeview)
        self.parent_widget.show_all()
        if not self.controller.get_store():
            return
        self._treeview.select_index(0)

    def _set_menu_items_sensitive(self, sensitive=True):
        for widget in (self.mnu_up, self.mnu_down, self.mnu_pageup, self.mnu_pagedown):
            widget.set_sensitive(sensitive)


    # EVENT HANDLERS #
    def _on_cursor_change(self, cursor):
        self._treeview.select_index(cursor.index)

    def _on_export(self, menu_item):
        # TODO: Get file name from user.
        try:
            self.controller.export_project_file(filename=None)
        except Exception, exc:
            self.controller.main_controller.view.show_error_dialog(
                title=_("Export failed"), message=str(exc)
            )

    def _on_export_open(self, menu_item):
        # TODO: Get file name from user.
        try:
            self.controller.export_project_file(filename=None, openafter=True)
        except Exception, exc:
            self.controller.main_controller.view.show_error_dialog(
                title=_("Export failed"), message=str(exc)
            )

    def _on_preview(self, menu_item):
        # TODO: Get file name from user.
        try:
            self.controller.export_project_file(filename=None, openafter=True, readonly=True)
        except Exception, exc:
            self.controller.main_controller.view.show_error_dialog(
                title=_("Preview failed"), message=str(exc)
            )

    def _on_style_set(self, widget, prev_style):
        # The following color change is to reduce the flickering seen when
        # changing units. It's not the perfect cure, but helps a lot.
        # http://bugs.locamotion.org/show_bug.cgi?id=1412
        self._treeview.modify_base(gtk.STATE_ACTIVE, widget.style.bg[gtk.STATE_NORMAL])
