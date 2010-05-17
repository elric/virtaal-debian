#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
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
import logging
import os
import re
from translate.convert import factory as convert_factory
from translate.storage import proj

from virtaal.common import GObjectWrapper
from virtaal.models import StoreModel
from virtaal.views import StoreView
from basecontroller import BaseController
from cursor import Cursor


# TODO: Create an event that is emitted when a cursor is created
class StoreController(BaseController):
    """The controller for all store-level activities."""

    __gtype_name__ = 'StoreController'
    __gsignals__ = {
        'store-loaded': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'store-saved':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
        'store-closed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ()),
    }

    # INITIALIZERS #
    def __init__(self, main_controller):
        GObjectWrapper.__init__(self)

        self.main_controller = main_controller
        self.main_controller.store_controller = self
        self._unit_controller = None # This is set by UnitController itself when it is created

        self.cursor = None
        self.handler_ids = {}
        self._modified = False
        self.project = None
        self.store = None
        self.view = StoreView(self)

        self._controller_register_id = self.main_controller.connect('controller-registered', self._on_controller_registered)


    # ACCESSORS #
    def get_nplurals(self, store=None):
        if not store:
            store = self.store
        return store and store.nplurals or 0

    def get_store(self):
        return self.store

    def get_unit_celleditor(self, unit):
        """Load the given unit in via the C{UnitController} and return
            the C{gtk.CellEditable} it creates."""
        return self.unit_controller.load_unit(unit)

    def is_modified(self):
        return self._modified

    def _get_unitcontroller(self):
        return self._unit_controller
    def _set_unitcontroller(self, unitcont):
        """@type unitcont: UnitController"""
        if self.unit_controller and 'unitview.unit-modified' in self.handler_ids:
            self.unit_controller.disconnect(self.handler_ids['unitview.unit-modified'])
        self._unit_controller = unitcont
        self.handler_ids['unitview.unit-modified'] = self.unit_controller.connect('unit-modified', self._unit_modified)
    unit_controller = property(_get_unitcontroller, _set_unitcontroller)


    # METHODS #
    def select_unit(self, unit, force=False):
        """Select the specified unit and scroll to it.
            Note that, because we change units via the cursor, the unit to
            select must be valid according to the cursor."""
        if self.cursor.deref() == unit and not force:
            # Unit is already selected; no need to do more work
            return

        i = 0
        try:
            i = self.store.get_units().index(unit)
        except Exception, exc:
            logging.debug('Unit not found:\n%s' % (exc))

        if force:
            self.cursor.force_index(i)
        else:
            self.cursor.index = i

    def open_file(self, filename, uri=''):
        extension = filename.split(os.extsep)[-1]
        if extension == 'zip':
            try:
                self.project = proj.Project(proj.BundleProjectStore(filename))
            except proj.InvalidBundleError, err:
                logging.exception('Unable to load project bundle')

            if not len(self.project.store.transfiles):
                # FIXME: Ask the user to select a source file to convert?
                if not len(self.project.store.sourcefiles):
                    raise proj.InvalidBundleError('No source or translatable files in bundle')
                self.project.convert_forward(self.project.store.sourcefiles[0])

            # FIXME: Ask the user which translatable file to open?
            transfile = self.project.get_file(self.project.store.transfiles[0])
            self.real_filename = transfile.name
            logging.info(
                'Editing translation file %s in bundle %s' %
                (os.path.split(self.real_filename)[-1], filename)
            )
            self.store = StoreModel(transfile, self)
        elif extension in convert_factory.converters:
            self.project = proj.Project()
            srcfile, srcfilename, transfile, transfilename = self.project.add_source_convert(filename)
            self.real_filename = transfile.name
            logging.info('Converted document %s to translatable file %s' % (srcfilename, self.real_filename))
            self.store = StoreModel(transfile, self)
        else:
            self.store = StoreModel(filename, self)

        if len(self.store.get_units()) < 1:
            raise Exception(_('The file contains nothing to translate.'))

        self._modified = False

        self.main_controller.set_force_saveas(False)
        # if file is a template force saveas
        pot_regexp = re.compile("\.pot(\.gz|\.bz2)?$")
        if pot_regexp.search(filename):
            self.main_controller.set_force_saveas(True)
            self.store._trans_store.filename = pot_regexp.sub('.po', filename)

        self.main_controller.set_saveable(self._modified)

        self.cursor = Cursor(self.store, self.store.stats['total'])

        self.view.load_store(self.store)
        self.view.show()

        self.emit('store-loaded')

    def save_file(self, filename=None):
        self.store.save_file(filename) # store.save_file() will raise an appropriate exception if necessary
        if self.project is not None:
            if filename is None:
                filename = self.real_filename
            proj_fname = self.project.get_proj_filename(filename)
            self.project.convert_forward(proj_fname)
        self._modified = False
        self.main_controller.set_saveable(False)
        self.emit('store-saved')

    def close_file(self):
        self.project = None
        self.store = None
        self._modified = False
        self.main_controller.set_saveable(False)
        self.view.hide() # This MUST be called BEFORE `self.cursor = None`
        self.emit('store-closed') # This should be emitted BEFORE `self.cursor = None` to allow any other modules to disconnect from the cursor
        self.cursor = None

    def revert_file(self):
        self.open_file(self.store.filename)

    def update_file(self, filename, uri=''):
        if not self.store:
            #FIXME: we should never allow updates if no file is already open
            self.store = StoreModel(filename, self)
        else:
            self.store.update_file(filename)

        self._modified = True
        self.main_controller.set_saveable(self._modified)
        self.main_controller.set_force_saveas(self._modified)

        self.cursor = Cursor(self.store, self.store.stats['total'])

        self.view.load_store(self.store)
        self.view.show()

        self.emit('store-loaded')

    def compare_stats(self, oldstats, newstats):
        #l10n: The heading of statistics before updating to the new template
        before = _("Before:")
        #l10n: The heading of statistics after updating to the new template
        after = _("After:")
        translated = _("Translated: %d")
        fuzzy = _("Fuzzy: %d")
        untranslated = _("Untranslated: %d")
        total = _("Total: %d")
        output = "%s\n\t%s\n\t%s\n\t%s\n\t%s\n" % (before, translated, fuzzy, untranslated, total)
        output += "%s\n\t%s\n\t%s\n\t%s\n\t%s" % (after, translated, fuzzy, untranslated, total)

        old_trans = len(oldstats['translated'])
        old_fuzzy = len(oldstats['fuzzy'])
        old_untrans = len(oldstats['untranslated'])
        old_total = old_trans + old_fuzzy + old_untrans

        new_trans = len(newstats['translated'])
        new_fuzzy = len(newstats['fuzzy'])
        new_untrans = len(newstats['untranslated'])
        new_total = new_trans + new_fuzzy + new_untrans

        output %= (old_trans, old_fuzzy, old_untrans, old_total,
                   new_trans, new_fuzzy, new_untrans, new_total)

        #l10n: this refers to updating a file to a new template (POT file)
        self.main_controller.show_info(_("File Updated"), output)


    # EVENT HANDLERS #
    def _on_controller_registered(self, main_controller, controller):
        if controller is main_controller.lang_controller:
            main_controller.disconnect(self._controller_register_id)
            main_controller.lang_controller.connect('source-lang-changed', self._on_source_lang_changed)
            main_controller.lang_controller.connect('target-lang-changed', self._on_target_lang_changed)

    def _on_source_lang_changed(self, _sender, langcode):
        self.store.set_source_language(langcode)

    def _on_target_lang_changed(self, _sender, langcode):
        self.store.set_target_language(langcode)

    def _unit_modified(self, emitter, unit):
        self._modified = True
        self.main_controller.set_saveable(self._modified)
