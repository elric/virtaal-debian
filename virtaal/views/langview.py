#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2011 Zuza Software Foundation
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

import os
import gobject
import gtk
import gtk.gdk
import logging

from virtaal.common import GObjectWrapper
from virtaal.models.langmodel import LanguageModel

from baseview import BaseView
from widgets.popupmenubutton import PopupMenuButton


class LanguageView(BaseView):
    """
    Manages the language selection on the GUI and communicates with its associated
    C{LanguageController}.
    """

    # INITIALIZERS #
    def __init__(self, controller):
        self.controller = controller
        self._init_gui()

    def _create_dialogs(self):
        from widgets.langselectdialog import LanguageSelectDialog
        from widgets.langadddialog import LanguageAddDialog
        langs = [LanguageModel(lc) for lc in LanguageModel.languages]
        langs.sort(key=lambda x: x.name)
        self.select_dialog = LanguageSelectDialog(langs, parent=self.controller.main_controller.view.main_window)
        self.select_dialog.btn_add.connect('clicked', self._on_addlang_clicked)

        self.add_dialog = LanguageAddDialog(parent=self.select_dialog.dialog)

    def _init_gui(self):
        self.menu = None
        self.popupbutton = PopupMenuButton()
        self.popupbutton.connect('toggled', self._on_button_toggled)

        self.controller.main_controller.view.main_window.connect(
            'style-set', self._on_style_set
        )
        if self.controller.recent_pairs:
            self.popupbutton.text = self._get_display_string(*self.controller.recent_pairs[0])

    def _init_menu(self):
        self.menu = gtk.Menu()
        self.popupbutton.set_menu(self.menu)

        self.recent_items = []
        for i in range(self.controller.NUM_RECENT):
            item = gtk.MenuItem('')
            item.connect('activate', self._on_pairitem_activated, i)
            self.recent_items.append(item)
        seperator = gtk.SeparatorMenuItem()
        self.other_item = gtk.MenuItem(_('_New Language Pair...'))
        self.other_item.connect('activate', self._on_other_activated)
        [self.menu.append(item) for item in (seperator, self.other_item)]
        self.update_recent_pairs()

        self.controller.main_controller.view.main_window.connect(
            'style-set', self._on_style_set
        )


    # METHODS #
    def _get_display_string(self, srclang, tgtlang):
        if self.popupbutton.get_direction() == gtk.TEXT_DIR_RTL:
            # We need to make sure we get the direction correct if the
            # language names are untranslated. The right-to-left embedding
            # (RLE) characters ensure that untranslated language names will
            # still diplay with the correct direction as they are present
            # in the interface.
            pairlabel = u'\u202b%s ← \u202b%s' % (srclang.name, tgtlang.name)
        else:
            pairlabel = u'%s → %s' % (srclang.name, tgtlang.name)
        # While it seems that the arrows are not well supported on Windows
        # systems, we fall back to using the French quotes. It automatically
        # does the right thing for RTL.
        if os.name == 'nt':
            pairlabel = u'%s » %s' % (srclang.name, tgtlang.name)
        return pairlabel

    def notify_same_langs(self):
        def notify():
            for s in [gtk.STATE_ACTIVE, gtk.STATE_NORMAL, gtk.STATE_PRELIGHT, gtk.STATE_SELECTED]:
                self.popupbutton.child.modify_fg(s, gtk.gdk.color_parse('#f66'))
        gobject.idle_add(notify)

    def notify_diff_langs(self):
        def notify():
            if hasattr(self, 'popup_default_fg'):
                fgcol = self.popup_default_fg
            else:
                fgcol = gtk.widget_get_default_style().fg
            for s in [gtk.STATE_ACTIVE, gtk.STATE_NORMAL, gtk.STATE_PRELIGHT, gtk.STATE_SELECTED]:
                self.popupbutton.child.modify_fg(s, fgcol[s])
        gobject.idle_add(notify)

    def show(self):
        """Add the managed C{PopupMenuButton} to the C{MainView}'s status bar."""
        statusbar = self.controller.main_controller.view.status_bar

        for child in statusbar.get_children():
            if child is self.popupbutton:
                return
        statusbar.pack_end(self.popupbutton, expand=False)
        statusbar.show_all()

    def focus(self):
        self.popupbutton.grab_focus()

    def update_recent_pairs(self):
        if not self.menu:
            self._init_menu()
        # Clear all menu items
        for i in range(self.controller.NUM_RECENT):
            item = self.recent_items[i]
            if item.parent is self.menu:
                item.get_child().set_text('')
                self.menu.remove(item)

        # Update menu items' strings
        i = 0
        for pair in self.controller.recent_pairs:
            if i not in range(self.controller.NUM_RECENT):
                break
            self.recent_items[i].get_child().set_text_with_mnemonic(
                "_%(accesskey)d. %(language_pair)s" % {
                    "accesskey": i + 1,
                    "language_pair": self._get_display_string(*pair)
                }
            )
            i += 1

        # Re-add menu items that have something to show
        for i in range(self.controller.NUM_RECENT):
            item = self.recent_items[i]
            if item.get_child().get_text():
                self.menu.insert(item, i)

        self.menu.show_all()
        self.popupbutton.text = self.recent_items[0].get_child().get_text()[3:]


    # EVENT HANDLERS #
    def _on_addlang_clicked(self, button):
        if not self.add_dialog.run():
            return

        err = self.add_dialog.check_input_sanity()
        if err:
            self.controller.main_controller.show_error(err)
            return

        name = self.add_dialog.langname
        code = self.add_dialog.langcode
        nplurals = self.add_dialog.nplurals
        plural = self.add_dialog.plural

        if self.add_dialog.langcode in LanguageModel.languages:
            raise Exception('Language code %s already used.' % (code))

        LanguageModel.languages[code] = (name, nplurals, plural)
        self.controller.new_langs.append(code)

        # Reload the language data in the selection dialog.
        self.select_dialog.clear_langs()
        langs = [LanguageModel(lc) for lc in LanguageModel.languages]
        langs.sort(key=lambda x: x.name)
        self.select_dialog.update_languages(langs)

    def _on_button_toggled(self, popupbutton):
        if not popupbutton.get_active():
            return
        detected = self.controller.get_detected_langs()
        if detected and len(detected) == 2 and detected[0] and detected[1]:
            logging.debug("Detected language pair: %s -> %s" % (detected[0].code, detected[1].code))
            if detected not in self.controller.recent_pairs:
                if len(self.controller.recent_pairs) >= self.controller.NUM_RECENT:
                    self.controller.recent_pairs[-1] = detected
                else:
                    self.controller.recent_pairs.append(detected)
        self.update_recent_pairs()

    def _on_other_activated(self, menuitem):
        if not getattr(self, 'select_dialog', None):
            self._create_dialogs()
        if self.select_dialog.run(self.controller.source_lang.code, self.controller.target_lang.code):
            self.controller.set_language_pair(
                self.select_dialog.get_selected_source_lang(),
                self.select_dialog.get_selected_target_lang()
            )
        self.controller.main_controller.unit_controller.view.targets[0].grab_focus()

    def _on_pairitem_activated(self, menuitem, item_n):
        logging.debug('Selected language pair: %s' % (self.recent_items[item_n].get_child().get_text()))
        pair = self.controller.recent_pairs[item_n]
        self.controller.set_language_pair(*pair)
        self.controller.main_controller.unit_controller.view.targets[0].grab_focus()

    def _on_style_set(self, widget, prev_style):
        if not hasattr(self, 'popup_default_fg'):
            self.popup_default_fg = widget.style.fg
