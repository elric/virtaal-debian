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

"""Contains the AutoCompletor class."""

import gobject
import gtk
import logging
import re
try:
    from collections import defaultdict
except ImportError:
    class defaultdict(dict):
        def __init__(self, default_factory=lambda: None):
            self.__factory = default_factory

        def __getitem__(self, key):
            if key in self:
                return super(defaultdict, self).__getitem__(key)
            else:
                return self.__factory()

from virtaal.controllers import BasePlugin


class AutoCompletor(object):
    """
    Does auto-completion of registered words in registered widgets.
    """

    wordsep_re = re.compile(r'\W+', re.UNICODE)

    MAX_WORDS = 10000
    DEFAULT_COMPLETION_LENGTH = 4 # The default minimum length of a word that may
                                  # be auto-completed.

    def __init__(self, main_controller, word_list=[], comp_len=DEFAULT_COMPLETION_LENGTH):
        """Constructor.

            @type  word_list: iterable
            @param word_list: A list of words that should be auto-completed."""
        self.main_controller = main_controller
        assert isinstance(word_list, list)
        self.comp_len = comp_len
        self._word_list = []
        self._word_freq = defaultdict(lambda: 0)
        self.add_words(word_list)
        self.widgets = set()

    def add_widget(self, widget):
        """Add a widget to the list of widgets to do auto-completion for."""
        if widget in self.widgets:
            return # Widget already added

        if isinstance(widget, gtk.TextView):
            self._add_text_view(widget)
            return

        raise ValueError("Widget type %s not supported." % (type(widget)))

    def usable(self, word):
        """Returns a value indicating if the given word should be kept as a
        suggestion for autocomplete."""
        return len(word) > self.comp_len + 2

    def add_words(self, words, update=True):
        """Add a word or words to the list of words to auto-complete."""
        for word in words:
            if self.usable(word):
                self._word_freq[word] += 1
        if update:
            self._update_word_list()

    def add_words_from_units(self, units):
        """Collect all words from the given translation units to use for
            auto-completion.

            @type  units: list
            @param units: The translation units to collect words from.
            """
        for unit in units:
            target = unit.target
            if not target:
                continue
            self.add_words(self.wordsep_re.split(target), update=False)
            if len(self._word_freq) > self.MAX_WORDS:
                break

        self._update_word_list()

    def autocomplete(self, word):
        for w in self._word_list:
            if w.startswith(word):
                return w, w[len(word):]
        return None, u''

    def clear_widgets(self):
        """Release all registered widgets from the spell of auto-completion."""
        for w in set(self.widgets):
            self.remove_widget(w)

    def clear_words(self):
        """Remove all registered words; effectively turns off auto-completion."""
        self._word_freq = []
        self._word_list = defaultdict(lambda: 0)

    def remove_widget(self, widget):
        """Remove a widget (currently only C{gtk.TextView}s are accepted) from
            the list of widgets to do auto-correction for.
            """
        if isinstance(widget, gtk.TextView) and widget in self.widgets:
            self._remove_textview(widget)

    def remove_words(self, words):
        """Remove a word or words from the list of words to auto-complete."""
        if isinstance(words, basestring):
            del self._word_freq[words]
            self._word_list.remove(words)
        else:
            for w in words:
                try:
                    del self._word_freq[w]
                    self._word_list.remove(w)
                except KeyError:
                    pass

    def _add_text_view(self, textview):
        """Add the given I{gtk.TextView} to the list of widgets to do auto-
            correction on."""
        id_dict_names = (
            '_textbuffer_insert_ids',
            '_textbuffer_delete_ids',
            '_textview_button_press_ids',
            '_textview_focus_out_ids',
            '_textview_key_press_ids',
            '_textview_move_cursor_ids'
        )
        for name in id_dict_names:
            if not hasattr(self, name):
                setattr(self, name, {})

        buffer = textview.get_buffer()
        handler_id = buffer.connect('insert-text', self._on_insert_text)
        self._textbuffer_insert_ids[buffer] = handler_id

        handler_id = buffer.connect('delete-range', self._on_delete_range)
        self._textbuffer_delete_ids[buffer] = handler_id

        handler_id = textview.connect('button-press-event', self._on_textview_button_press)
        self._textview_button_press_ids[textview] = handler_id

        handler_id = textview.connect('key-press-event', self._on_textview_keypress)
        self._textview_key_press_ids[textview] = handler_id

        handler_id = textview.connect('focus-out-event', self._on_textview_focus_out)
        self._textview_focus_out_ids[textview] = handler_id

        handler_id = textview.connect('move-cursor', self._on_textview_move_cursor)
        self._textview_move_cursor_ids[textview] = handler_id

        self.widgets.add(textview)

    def _check_delete_selection(self, buffer):
        """Deletes the current selection if said selection was created by the auto-completor."""
        suggestion = getattr(buffer, '_suggestion', None)
        if suggestion:
            buffer.delete_selection(False, True)
            buffer._suggestion = None

    def _on_insert_text(self, buffer, iter, text, length):
        if self.wordsep_re.match(text):
            return
        # We are only interested in single character insertions, otherwise we
        # react similarly for paste and similar events
        if len(text.decode('utf-8')) > 1:
            return

        prefix = unicode(buffer.get_text(buffer.get_start_iter(), iter) + text)
        postfix = unicode(buffer.get_text(iter, buffer.get_end_iter()))

        # Quick fix to check that we don't autocomplete in the middle of a word.
        right_lim = len(postfix) > 0 and postfix[0] or ' '
        if not self.wordsep_re.match(right_lim):
            return

        lastword = self.wordsep_re.split(prefix)[-1]

        if len(lastword) >= self.comp_len:
            completed_word, word_postfix = self.autocomplete(lastword)
            if completed_word == lastword:
                buffer._suggestion = None
                return

            if completed_word:
                completed_prefix = prefix[:-len(lastword)] + completed_word
                # Updating of the buffer is deferred until after this signal
                # and its side effects are taken care of. We abuse
                # gobject.idle_add for that.
                def suggest_completion():
                    # The undo_controller.{disable,enable}() calls ensures that the insertion
                    # of the suggestion string is not added to the undo stack.
                    # See _on_delete_range() below for a related undo stack (delete event) hack.
                    self.main_controller.undo_controller.disable()
                    buffer.handler_block(self._textbuffer_insert_ids[buffer])
                    #logging.debug('buffer.insert_at_cursor("%s")' % (word_postfix))
                    buffer.insert_at_cursor(word_postfix)
                    buffer.handler_unblock(self._textbuffer_insert_ids[buffer])
                    self.main_controller.undo_controller.enable()

                    sel_iter_start = buffer.get_iter_at_offset(len(prefix))
                    sel_iter_end   = buffer.get_iter_at_offset(len(prefix+word_postfix))
                    buffer.select_range(sel_iter_start, sel_iter_end)

                    buffer._suggestion = (sel_iter_start, sel_iter_end)
                    return False

                gobject.idle_add(suggest_completion)
            else:
                buffer._suggestion = None
        else:
            buffer._suggestion = None

    def _on_delete_range(self, buf, start_iter, end_iter):
        suggestion = getattr(buf, '_suggestion', None)
        if suggestion:
            selection = buf.get_selection_bounds()
            if selection and suggestion[0].equal(selection[0]) and suggestion[1].equal(selection[1]):
                # This removes the deletion of the suggestion from the undo stack.
                # See _on_insert_text() above for a related undo stack (insert event) hack.
                self.main_controller.undo_controller.model.pop(permanent=True)
                return False
            else:
                self._check_delete_selection(buf)
        buf._suggestion = None

    def _on_textview_button_press(self, textview, event):
        self._check_delete_selection(textview.get_buffer())

    def _on_textview_focus_out(self, textview, event):
        self._check_delete_selection(textview.get_buffer())

    def _on_textview_move_cursor(self, textview, step_size, count, expand_selection):
        self._check_delete_selection(textview.get_buffer())

    def _on_textview_keypress(self, textview, event):
        """Catch tabs to the C{gtk.TextView} and make it keep the current selection."""
        iters = textview.get_buffer().get_selection_bounds()

        if not iters:
            return False
        if event.keyval == gtk.keysyms.Tab:
            buf = textview.get_buffer()
            completion = buf.get_text(iters[0], iters[1])
            buf.place_cursor(iters[1])
            buf.move_mark_by_name('selection_bound', iters[1])
            return True
        elif event.state & gtk.gdk.CONTROL_MASK and \
                event.keyval == gtk.keysyms.Z or event.keyval== gtk.keysyms.BackSpace:
            # An undo/delete event will unselect the suggestion and make it hang
            # around. Therefore we need to remove the suggestion manually.
            self._check_delete_selection(textview.get_buffer())
            return False

    def _remove_textview(self, textview):
        """Remove the given C{gtk.TextView} from the list of widgets to do
            auto-correction on.
            """
        if not hasattr(self, '_textbuffer_insert_ids'):
            return
        # Disconnect the "insert-text" event handler
        buffer = textview.get_buffer()
        buffer.disconnect(self._textbuffer_insert_ids[buffer])

        if not hasattr(self, '_textbuffer_delete_ids'):
            return
        # Disconnect the "delete-range" event handler
        buffer.disconnect(self._textbuffer_delete_ids[buffer])

        if not hasattr(self, '_textview_focus_out_ids'):
            return
        # Disconnect the "focus-out-event" event handler
        textview.disconnect(self._textview_focus_out_ids[textview])

        if not hasattr(self, '_textview_key_press_ids'):
            return
        # Disconnect the "key-press-event" event handler
        textview.disconnect(self._textview_key_press_ids[textview])

        if not hasattr(self, '_textview_move_cursor_ids'):
            return
        # Disconnect the "move-cursor" event handler
        textview.disconnect(self._textview_move_cursor_ids[textview])

        self.widgets.remove(textview)

    def _update_word_list(self):
        """Update and sort found words according to frequency."""
        wordlist = self._word_freq.items()
        wordlist.sort(key=lambda x:x[1])
        self._word_list = [items[0] for items in wordlist]


class Plugin(BasePlugin):
    display_name = _('AutoCompletor')
    version = 0.1

    # INITIALIZERS #
    def __init__(self, internal_name, main_controller):
        self.internal_name = internal_name
        self.main_controller = main_controller

        self._init_plugin()

    def _init_plugin(self):
        from virtaal.common import pan_app
        self.autocomp = AutoCompletor(self.main_controller)

        self._store_loaded_id = self.main_controller.store_controller.connect('store-loaded', self._on_store_loaded)

        for target in self.main_controller.unit_controller.view.targets:
            self.autocomp.add_widget(target)

        if self.main_controller.store_controller.get_store():
            # Connect to already loaded store. This happens when the plug-in is enabled after loading a store.
            self._on_store_loaded(self.main_controller.store_controller)


    # METHDOS #
    def destroy(self):
        """Remove all signal-connections."""
        self.autocomp.clear_words()
        self.autocomp.clear_widgets()
        self.main_controller.store_controller.disconnect(self._store_loaded_id)
        if getattr(self, '_cursor_changed_id', None):
            self.store_cursor.disconnect(self._cursor_changed_id)


    # EVENT HANDLERS #
    def _on_cursor_change(self, cursor):
        def add_widgets():
            if hasattr(self, 'lastunit'):
                if self.lastunit.hasplural():
                    for target in self.lastunit.target:
                        if target:
                            logging.debug('Adding words: %s' % (self.autocomp.wordsep_re.split(unicode(target))))
                            self.autocomp.add_words(self.autocomp.wordsep_re.split(unicode(target)))
                else:
                    if self.lastunit.target:
                        logging.debug('Adding words: %s' % (self.autocomp.wordsep_re.split(unicode(self.lastunit.target))))
                        self.autocomp.add_words(self.autocomp.wordsep_re.split(unicode(self.lastunit.target)))
            self.lastunit = cursor.deref()
        gobject.idle_add(add_widgets)

    def _on_store_loaded(self, storecontroller):
        self.autocomp.add_words_from_units(storecontroller.get_store().get_units())

        if hasattr(self, '_cursor_changed_id'):
            self.store_cursor.disconnect(self._cursor_changed_id)
        self.store_cursor = storecontroller.cursor
        self._cursor_changed_id = self.store_cursor.connect('cursor-changed', self._on_cursor_change)
        self._on_cursor_change(self.store_cursor)
