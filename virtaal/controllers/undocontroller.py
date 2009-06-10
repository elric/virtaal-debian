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

import gobject
import gtk
import logging
from gtk import gdk

from virtaal.common import GObjectWrapper
from virtaal.models import UndoModel

from basecontroller import BaseController


class UndoController(BaseController):
    """Contains "undo" logic."""

    __gtype_name__ = 'UndoController'


    # INITIALIZERS #
    def __init__(self, main_controller):
        """Constructor.
            @type main_controller: virtaal.controllers.MainController"""
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        self.main_controller.undo_controller = self
        self.unit_controller = self.main_controller.store_controller.unit_controller

        self.enabled = True
        self.model = UndoModel(self)
        self._paste_undo_info = None

        self._setup_key_bindings()
        self._connect_undo_signals()

    def _connect_undo_signals(self):
        # First connect to the unit controller
        self.unit_controller.connect('unit-delete-text', self._on_unit_delete_text)
        self.unit_controller.connect('unit-insert-text', self._on_unit_insert_text)
        self.unit_controller.connect('unit-paste-start', self._on_unit_paste_start)
        self.main_controller.store_controller.connect('store-loaded', self._on_store_loaded)

        mainview = self.main_controller.view
        mainview.gui.get_widget('menu_edit').set_accel_group(self.accel_group)
        mainview.gui.get_widget('mnu_undo').set_accel_path('<Virtaal>/Edit/Undo')
        mainview.gui.get_widget('mnu_undo').connect('activate', self._on_undo_activated)

    def _setup_key_bindings(self):
        """Setup Gtk+ key bindings (accelerators).
            This method *may* need to be moved into a view object, but if it is,
            it will be the only functionality in such a class. Therefore, it
            is done here. At least for now."""
        gtk.accel_map_add_entry("<Virtaal>/Edit/Undo", gtk.keysyms.z, gdk.CONTROL_MASK)

        self.accel_group = gtk.AccelGroup()
        # The following line was commented out, because it caused a double undo when pressing
        # Ctrl+Z, but only one if done through the menu item. This way it all works as expected.
        #self.accel_group.connect_by_path("<Virtaal>/Edit/Undo", self._on_undo_activated)

        mainview = self.main_controller.view # FIXME: Is this acceptable?
        mainview.add_accel_group(self.accel_group)


    # DECORATORS #
    def if_enabled(method):
        def enabled_method(self, *args, **kwargs):
            if self.enabled:
                return method(self, *args, **kwargs)
        return enabled_method


    # METHODS #
    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True

    def remove_blank_undo(self):
        """Removes items from the top of the undo stack with no C{value} or
            C{action} values. The "top of the stack" is one of the top 2 items.

            This is a convenience method that can be used by any code that
            directly sets unit values."""
        if not self.model.undo_stack:
            return

        head = self.model.head()
        if 'action' in head and not head['action'] or True:
            self.model.pop(permanent=True)
            return

        item = self.model.peek(offset=-1)
        if 'action' in item and not item['action'] or True:
            self.model.index -= 1
            self.model.undo_stack.remove(item)

    def record_stop(self):
        self.model.record_stop()

    def record_start(self):
        self.model.record_start()

    def _disable_unit_signals(self):
        """Disable all signals emitted by the unit view.
            This should always be followed, as soon as possible, by
            C{self._enable_unit_signals()}."""
        self.unit_controller.view.disable_signals()

    def _enable_unit_signals(self):
        """Enable all signals emitted by the unit view.
            This should always follow, as soon as possible, after a call to
            C{self._disable_unit_signals()}."""
        self.unit_controller.view.enable_signals()

    def _perform_undo(self, undo_info):
        self._select_unit(undo_info['unit'])

        #if 'desc' in undo_info:
        #    logging.debug('Description: %s' % (undo_info['desc']))

        self._disable_unit_signals()
        undo_info['action'](undo_info['unit'])
        self._enable_unit_signals()
        textbox = self.unit_controller.view.targets[self.unit_controller.view.focused_target_n]
        textbox.refresh(cursor_pos=undo_info['cursorpos'])

    def _select_unit(self, unit):
        """Select the given unit in the store view.
            This is to select the unit where the undo-action took place.
            @type  unit: translate.storage.base.TranslationUnit
            @param unit: The unit to select in the store view."""
        self.main_controller.select_unit(unit, force=True)


    # EVENT HANDLERS #
    def _on_store_loaded(self, storecontroller):
        self.model.clear()

    @if_enabled
    def _on_undo_activated(self, *args):
        undo_info = self.model.pop()
        if not undo_info:
            return

        if isinstance(undo_info, list):
            for ui in reversed(undo_info):
                self._perform_undo(ui)
        else:
            self._perform_undo(undo_info)

    @if_enabled
    def _on_unit_delete_text(self, unit_controller, unit, start_offset, end_offset, deleted, parent, cursor_pos, elem, target_num):
        if self._paste_undo_info:
            self.model.push(self._paste_undo_info)
            self._paste_undo_info = None
            return

        #logging.debug('_on_unit_delete_text(offsets=(%d, %d), deleted="%s", elem=%s, target_n=%d)' % (start_offset, end_offset, deleted, repr(elem), target_num))

        def undo_action(unit):
            #logging.debug('(undo) %s.insert(%d, "%s")' % (repr(elem), start_offset, deleted))
            if parent is None:
                elem.sub = deleted.sub
                return
            parent_offset = elem.elem_offset(parent)
            prel_offset = elem.gui_info.gui_to_tree_index(start_offset) - parent_offset
            parent.insert(prel_offset, deleted)
            parent.prune()

        desc = 'offsets=(%d, %d), deleted="%s", elem=%s' % (start_offset, end_offset, deleted, repr(elem))
        self.model.push({
            'action': undo_action,
            'cursorpos': cursor_pos,
            'desc': desc,
            'targetn': target_num,
            'unit': unit,
        })

    @if_enabled
    def _on_unit_insert_text(self, unit_controller, unit, ins_text, offset, elem, target_num):
        if self._paste_undo_info:
            return

        #logging.debug('_on_unit_insert_text(ins_text="%s", offset=%d, elem=%s, target_n=%d)' % (ins_text, offset, repr(elem), target_num))

        def undo_action(unit):
            tree_offset = elem.gui_info.gui_to_tree_index(offset)
            #logging.debug('(undo) %s.delete_range(%d, %d)' % (repr(elem), tree_offset, tree_offset+len(ins_text)))
            elem.delete_range(tree_offset, tree_offset+len(ins_text))
            elem.prune()

        desc = 'ins_text="%s", offset=%d, elem=%s' % (ins_text, offset, repr(elem))
        self.model.push({
            'action': undo_action,
            'desc': desc,
            'unit': unit,
            'targetn': target_num,
            'cursorpos': offset
        })

    @if_enabled
    def _on_unit_paste_start(self, _unit_controller, unit, old_text, offsets, target_num):
        if offsets['insert_offset'] == offsets['selection_offset']:
            # If there is no selection, a paste is equivalent to an insert action
            return

        self._paste_undo_info = {
            'unit': unit,
            'targetn': target_num,
            'cursorpos': offsets['insert_offset']
        }
