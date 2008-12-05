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
import re

from virtaal import markup
from virtaal import rendering

from baseview import BaseView
from widgets.label_expander import LabelExpander


class UnitView(gtk.EventBox, gtk.CellEditable, BaseView):
    """View for translation units and its actions."""

    __gtype_name__ = "UnitView"
    __gsignals__ = {
        'modified': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
    }

    # A regular expression to help us find a meaningful place to position the
    # cursor initially.
    first_word_re = re.compile("(?m)(?u)^(<[^>]+>|\\\\[nt]|[\W$^\n])*(\\b|\\Z)")

    # INITIALIZERS #
    def __init__(self, controller, unit):
        gtk.EventBox.__init__(self)
        self.controller = controller

        self.gladefilename, self.gui = self.load_glade_file(["virtaal", "virtaal.glade"], root='UnitEditor', domain="virtaal")
        self.sources = []
        self.targets = []
        self.options = {}
        self._get_widgets()
        self.load_unit(unit)


    # METHODS #
    def copy_original(self, text_view):
        buf = text_view.get_buffer()
        position = buf.props.cursor_position
        lang = factory.getlanguage(self.targetlang)
        new_source = lang.punctranslate(self._unit.source)
        # if punctranslate actually changed something, let's insert that as an
        # undo step
        if new_source != self._unit.source:
            buf.set_text(markup.escape(self._unit.source))
            # TODO: consider a better position to return to on undo
            undo_buffer.merge_actions(buf, position)
        buf.set_text(markup.escape(new_source))
        undo_buffer.merge_actions(buf, position)
        unit_layout.focus_text_view(text_view)
        return False

    def do_start_editing(self, *_args):
        """C{gtk.CellEditable.start_editing()"""
        self.targets[0].grab_focus()

        buf = self.targets[0].get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter())

        translation_start = self.first_word_re.match(text).span()[1]
        buf.place_cursor(buf.get_iter_at_offset(translation_start))

    def load_unit(self, unit):
        """Load a GUI (C{gtk.CellEditable}) for the given unit."""
        if not unit:
            return None

        self.unit = unit
        self._get_widgets()
        self._build_default_editor()
        self.widgets['tbl_editor'].reparent(self)

        for target in self.targets:
            target.connect('key-press-event', self._on_text_view_key_press_event)
            target.get_buffer().connect("changed", self._on_modify)

        for option in self.options.values():
            option.connect("toggled", self._on_modify)

        self._modified = False
        self.connect('key-press-event', self._on_key_press_event)

    def show(self):
        self.show()

    def _build_default_editor(self):
        """Build the default editor with the following components:
            - A C{gtk.TextView} for each source
            - A C{gtk.TextView} for each target
            - A C{gtk.ToggleButton} for the fuzzy option
            - A C{widgets.LabelExpander} for programmer notes
            - A C{widgets.LabelExpander} for translator notes
            - A C{widgets.LabelExpander} for context info"""
        self._layout_add_notes('programmer')
        self._layout_add_sources()
        self._layout_add_context_info()
        self._layout_add_targets()
        self._layout_add_notes('translator')
        self._layout_add_fuzzy()

    def _get_widgets(self):
        """Load the Glade file and get the widgets we would like to use."""
        self.widgets = {}

        widget_names = ('tbl_editor', 'vbox_middle', 'vbox_sources', 'vbox_targets', 'vbox_options')

        for name in widget_names:
            self.widgets[name] = self.gui.get_widget(name)


    # GUI BUILDING CODE #
    def _create_textbox(self, text='', editable=True, scroll_policy=gtk.POLICY_AUTOMATIC):
        textview = gtk.TextView()
        textview.set_editable(editable)
        textview.set_wrap_mode(gtk.WRAP_WORD)
        textview.set_border_window_size(gtk.TEXT_WINDOW_TOP, 1)
        textview.set_left_margin(2)
        textview.set_right_margin(2)
        textview.get_buffer().set_text(text)

        scrollwnd = gtk.ScrolledWindow()
        scrollwnd.set_policy(gtk.POLICY_NEVER, scroll_policy)
        scrollwnd.connect('key-press-event', self._on_key_press_event_enter)
        scrollwnd.add(textview)

        return scrollwnd

    def _layout_add_notes(self, origin):
        textbox = self._create_textbox(
                self.unit.getnotes(origin),
                editable=False,
                scroll_policy=gtk.POLICY_NEVER
            )
        textview = textbox.get_child()
        labelexpander = LabelExpander(textbox, lambda *args: self.unit.getnotes(origin))

    def _layout_add_sources(self):
        num_sources = 1
        if self.unit.hasplural():
            num_sources = len(self.unit.source.strings)

        self.sources = []
        for i in range(num_sources):
            sourcestr = ''
            if self.unit.hasplural():
                sourcestr = self.unit.source.strings[i]
            elif i == 0:
                sourcestr = self.unit.source
            else:
                raise IndexError()

            source = self._create_textbox(
                    markup.escape(sourcestr),
                    editable=False,
                    scroll_policy=gtk.POLICY_NEVER
                )
            textview = source.get_child()
            textview.modify_font(rendering.get_source_font_description())
            # This causes some problems, so commented out for now
            #textview.get_pango_context().set_font_description(rendering.get_source_font_description())
            textview.get_pango_context().set_language(rendering.get_source_language())
            self.widgets['vbox_sources'].add(source)
            self.sources.append(textview)

    def _layout_add_context_info(self):
        textbox = self._create_textbox(
                self.unit.getcontext(),
                editable=False,
                scroll_policy=gtk.POLICY_NEVER
            )
        textview = textbox.get_child()
        labelexpander = LabelExpander(textbox, lambda *args: self.unit.getcontext())

    def _layout_add_targets(self):
        num_targets = 1
        if self.unit.hasplural():
            self.controller.nplurals

        def on_text_view_n_press_event(text_view, event):
            """Handle special keypresses in the textarea."""
            # Automatically move to the next line if \n is entered

            if event.keyval == gtk.keysyms.n:
                buf = text_view.get_buffer()
                curpos = buf.props.cursor_position
                lastchar = buf.get_text(
                        buf.get_iter_at_offset(curpos-1),
                        buf.get_iter_at_offset(curpos)
                    )
                if lastchar == "\\":
                    buf.insert_at_cursor('n\n')
                    text_view.scroll_mark_onscreen(buf.get_insert())
                    return True
            return False

        self.targets = []
        for i in range(num_targets):
            if self.unit.hasplural() and self.controller.nplurals != len(self.unit.target.strings):
                targets = self.controller.nplurals * [u'']
                targets[:len(self.unit.target.strings)] = self.unit.target.strings
                self.unit.target = targets

            targetstr = ''
            if self.unit.hasplural():
                targetstr = self.unit.target[i]
            elif i == 0:
                targetstr = self.unit.target
            else:
                raise IndexError()

            target = self._create_textbox(
                    markup.escape(targetstr),
                    editable=True,
                    scroll_policy=gtk.POLICY_AUTOMATIC
                )
            textview = target.get_child()
            textview.modify_font(rendering.get_target_font_description())
            textview.get_pango_context().set_font_description(rendering.get_target_font_description())
            textview.get_pango_context().set_language(rendering.get_target_language())
            textview.connect('key-press-event', on_text_view_n_press_event)

            self.widgets['vbox_targets'].add(target)
            self.targets.append(textview)

    def _layout_add_fuzzy(self):
        def on_toggled(widget, *_args):
            if widget.get_active():
                set_option(True)
            else:
                set_option(False)

        check_button = gtk.CheckButton(label=_('F_uzzy'))
        check_button.connect('toggled', on_toggled)
        check_button.set_active(self.unit.isfuzzy())
        # FIXME: not allowing focus will probably raise various issues related to keyboard accesss.
        check_button.set_property("can-focus", False)

        self.options['fuzzy'] = check_button
        self.widgets['vbox_options'].add(check_button)


    # EVENT HANLDERS #
    def _on_modify(self, _buf):
        self.emit('modified')

    def _on_key_press_event(self, _widget, event, *_args):
        if event.keyval == gtk.keysyms.Return or event.keyval == gtk.keysyms.KP_Enter:
            self.must_advance = True
            self.editing_done()
            return True
        return False

    def _on_key_press_event_enter(self, widget, event, *_args):
        if event.keyval == gtk.keysyms.Return or event.keyval == gtk.keysyms.KP_Enter:
            widget.parent.emit('key-press-event', event)
            return True
        return False

    def _on_text_view_key_press_event(self, widget, event, *_args):
        # Alt-Down
        if event.keyval == gtk.keysyms.Down and event.state & gtk.gdk.MOD1_MASK:
            gobject.idle_add(self.copy_original, widget)
            return True
        return False
