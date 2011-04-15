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
import logging
import re
from gobject import idle_add, PARAM_READWRITE, SIGNAL_RUN_FIRST, TYPE_PYOBJECT
from translate.lang import factory

from virtaal.common import GObjectWrapper

import rendering
from baseview import BaseView
from widgets.textbox import TextBox
from widgets.listnav import ListNavigator


class UnitView(gtk.EventBox, GObjectWrapper, gtk.CellEditable, BaseView):
    """View for translation units and its actions. It should not be used at
    all when no current unit is being edited. """

    __gtype_name__ = "UnitView"
    __gsignals__ = {
        'delete-text':    (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT, TYPE_PYOBJECT, int, int, TYPE_PYOBJECT, int)),
        'insert-text':    (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT, int, TYPE_PYOBJECT, int)),
        'paste-start':    (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT, TYPE_PYOBJECT, int)),
        'modified':       (SIGNAL_RUN_FIRST, None, ()),
        'unit-done':      (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'targets-created':(SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'sources-created':(SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'target-focused': (SIGNAL_RUN_FIRST, None, (int,)),
        'textview-language-changed': (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT, TYPE_PYOBJECT)),
    }
    __gproperties__ = {
        'editing-canceled': (bool, 'Editing cancelled', 'Editing was cancelled', False, PARAM_READWRITE),
    }

    first_word_re = re.compile("(?m)(?u)^(<[^>]+>|\\\\[nt]|[\W$^\n])*(\\b|\\Z)")
    """A regular expression to help us find a meaningful place to position the
        cursor initially."""

    MAX_SOURCES = 6
    """The number of text boxes to manage as sources."""
    MAX_TARGETS = 6
    """The number of text boxes to manage as targets."""

    # INITIALIZERS #
    def __init__(self, controller):
        gtk.EventBox.__init__(self)
        GObjectWrapper.__init__(self)

        self.controller = controller
        self._focused_target_n = None
        self.gladefilename, self.gui = self.load_glade_file(["virtaal", "virtaal.glade"], root='UnitEditor', domain="virtaal")

        self.must_advance = False
        self._modified = False

        self.connect('key-press-event', self._on_key_press_event)
        # We automatically inherrit the tooltip from the Treeview, so we have
        # to show our own custom one to not have a tooltip obscuring things
        invisible_tooltip = gtk.Window(gtk.WINDOW_POPUP)
        invisible_tooltip.resize(1,1)
        invisible_tooltip.set_opacity(0)
        self.set_tooltip_window(invisible_tooltip)
        self.connect('query-tooltip', self._on_query_tooltip)

        self._widgets = {
            'context_info': None,
            'state': None,
            'notes': {},
            'sources': [],
            'targets': []
        }
        self._get_widgets()
        self._widgets['vbox_editor'].reparent(self)
        self._setup_menus()
        self.unit = None

    def _setup_menus(self):
        def get_focused(widgets):
            for textview in widgets:
                if textview.is_focus():
                    return textview
            return None

        clipboard = gtk.Clipboard(selection=gtk.gdk.SELECTION_CLIPBOARD)
        def on_cut(menuitem):
            focused = get_focused(self.targets)
            if focused is not None:
                focused.get_buffer().cut_clipboard(clipboard, True)
        def on_copy(menuitem):
            focused = get_focused(self.targets + self.sources)
            if focused is not None:
                focused.get_buffer().copy_clipboard(clipboard)
        def on_paste(menuitem):
            focused = get_focused(self.targets)
            if focused is not None:
                focused.get_buffer().paste_clipboard(clipboard, None, True)

        maingui = self.controller.main_controller.view.gui
        self.mnu_cut = maingui.get_widget('mnu_cut')
        self.mnu_copy = maingui.get_widget('mnu_copy')
        self.mnu_paste = maingui.get_widget('mnu_paste')

        self.mnu_cut.connect('activate', on_cut)
        self.mnu_copy.connect('activate', on_copy)
        self.mnu_paste.connect('activate', on_paste)

        # And now for the "Transfer from source" and placeable selection menu items
        mnu_next = maingui.get_widget('mnu_placnext')
        mnu_prev = maingui.get_widget('mnu_placprev')
        mnu_transfer = maingui.get_widget('mnu_transfer')
        self.mnu_next = mnu_next
        self.mnu_prev = mnu_prev
        self.mnu_transfer = mnu_transfer
        menu_edit = maingui.get_widget('menu_edit')

        def on_next(*args):
            self.targets[self.focused_target_n].move_elem_selection(1)
        def on_prev(*args):
            self.targets[self.focused_target_n].move_elem_selection(-1)
        def on_transfer(*args):
            ev = gtk.gdk.Event(gtk.gdk.KEY_PRESS)
            ev.state = gtk.gdk.MOD1_MASK
            ev.keyval = gtk.keysyms.Down
            ev.window = self.targets[self.focused_target_n].get_window(gtk.TEXT_WINDOW_WIDGET)
            ev.put()
        mnu_next.connect('activate', on_next)
        mnu_prev.connect('activate', on_prev)
        mnu_transfer.connect('activate', on_transfer)

        gtk.accel_map_add_entry("<Virtaal>/Edit/Next Placeable", gtk.keysyms.Right, gtk.gdk.MOD1_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Edit/Prev Placeable", gtk.keysyms.Left, gtk.gdk.MOD1_MASK)
        gtk.accel_map_add_entry("<Virtaal>/Edit/Transfer", gtk.keysyms.Down, gtk.gdk.MOD1_MASK)

        accel_group = menu_edit.get_accel_group()
        if not accel_group:
            accel_group = gtk.AccelGroup()

        self.controller.main_controller.view.add_accel_group(accel_group)
        menu_edit.set_accel_group(accel_group)
        mnu_next.set_accel_path("<Virtaal>/Edit/Next Placeable")
        mnu_prev.set_accel_path("<Virtaal>/Edit/Prev Placeable")
        mnu_transfer.set_accel_path("<Virtaal>/Edit/Transfer")

        # Disable the menu items to start with, because we can't assume that a
        # store is loaded. See _set_menu_items_sensitive() for more activation.
        self._set_menu_items_sensitive(False)

        def on_store_closed(*args):
            mnu_next.set_sensitive(False)
            mnu_prev.set_sensitive(False)
            mnu_transfer.set_sensitive(False)
            self.mnu_cut.set_sensitive(False)
            self.mnu_copy.set_sensitive(False)
            self.mnu_paste.set_sensitive(False)
        def on_store_loaded(*args):
            mnu_next.set_sensitive(True)
            mnu_prev.set_sensitive(True)
            mnu_transfer.set_sensitive(True)
            self.mnu_cut.set_sensitive(True)
            self.mnu_copy.set_sensitive(True)
            self.mnu_paste.set_sensitive(True)
        self.controller.main_controller.store_controller.connect('store-closed', on_store_closed)
        self.controller.main_controller.store_controller.connect('store-loaded', on_store_loaded)


    # ACCESSORS #
    def is_modified(self):
        return self._modified

    def _get_focused_target_n(self):
        return self._focused_target_n
    def _set_focused_target_n(self, target_n):
        self.focus_text_view(self.targets[target_n])
    focused_target_n = property(_get_focused_target_n, _set_focused_target_n)

    def get_target_n(self, n):
        return self.targets[n].get_text()

    def set_target_n(self, n, newtext, cursor_pos=-1):
        # TODO: Save cursor position and set after assignment
        self.targets[n].set_text(newtext)
        if cursor_pos > -1:
            self.targets[n].buffer.place_cursor(self.targets[n].buffer.get_iter_at_offset(cursor_pos))

    sources = property(lambda self: self._widgets['sources'])
    targets = property(lambda self: self._widgets['targets'])


    # METHODS #
    def copy_original(self, textbox):
        if textbox.selector_textbox is not textbox and \
            textbox.selector_textbox.selected_elem is not None:
            textbox.insert_translation(textbox.selector_textbox.selected_elem)
            textbox.move_elem_selection(1)
            return

        undocontroller = self.controller.main_controller.undo_controller
        lang = factory.getlanguage(self.controller.main_controller.lang_controller.target_lang.code)

        selector_textbox_index = textbox.selector_textboxes.index(textbox.selector_textbox)
        tgt = self.unit.rich_source[selector_textbox_index].copy()
        placeables_controller = self.controller.main_controller.placeables_controller
        parsers = placeables_controller.get_parsers_for_textbox(textbox)
        placeables_controller.apply_parsers(tgt, parsers)
        if textbox.role == 'target':
            for plac in placeables_controller.non_target_placeables:
                tgt.remove_type(plac)
        tgt.prune()

        punctgt = tgt.copy()
        punctgt.map(
            lambda e: e.apply_to_strings(lang.punctranslate),
            lambda e: e.isleaf() and e.istranslatable
        )

        if punctgt != tgt:
            undocontroller.push_current_text(textbox)
            textbox.set_text(tgt)
            tgt = punctgt

        undocontroller.push_current_text(textbox)
        textbox.set_text(tgt)

        textbox.refresh_cursor_pos = self._get_editing_start_pos(textbox.elem)
        textbox.refresh()

        return False

    def do_start_editing(self, *_args):
        """C{gtk.CellEditable.start_editing()}"""
        self.focus_text_view(self.targets[0])

    def do_editing_done(self, *_args):
        pass

    def focus_text_view(self, textbox):
        textbox.grab_focus()

        text = textbox.get_text()
        translation_start = self._get_editing_start_pos(textbox.elem)
        textbox.buffer.place_cursor(textbox.buffer.get_iter_at_offset(translation_start))

        self._focused_target_n = self.targets.index(textbox)
        #logging.debug('emit("target-focused", focused_target_n=%d)' % (self._focused_target_n))
        self.emit('target-focused', self._focused_target_n)

    def load_unit(self, unit):
        """Load a GUI (C{gtk.CellEditable}) for the given unit."""
        assert unit
        if unit is None:
            logging.error("UnitView can't load a None unit")

        if unit is self.unit:
            return

        #logging.debug('emit("unit-done", self.unit=%s)' % (self.unit))
        if self.unit:
            self.emit('unit-done', self.unit)
        for src in self.sources:
            src.select_elem(elem=None)

        self.unit = unit
        self.disable_signals(['modified', 'insert-text', 'delete-text'])
        self._update_editor_gui()
        self.enable_signals(['modified', 'insert-text', 'delete-text'])

        for i in range(len(self.targets)):
            self.targets[i]._source_text = unit.source # FIXME: Find a better way to do this!

        self._modified = False

    def modified(self):
        self._modified = True
        #logging.debug('emit("modified")')
        self.emit('modified')

    def show(self):
        super(UnitView, self).show()

    def update_languages(self):
        srclang = self.controller.main_controller.lang_controller.source_lang.code
        tgtlang = self.controller.main_controller.lang_controller.target_lang.code

        for textview in self.sources:
            self._update_textview_language(textview, srclang)
            textview.modify_font(rendering.get_source_font_description())
            # This causes some problems, so commented out for now
            #textview.get_pango_context().set_font_description(rendering.get_source_font_description())
        for textview in self.targets:
            self._update_textview_language(textview, tgtlang)
            textview.modify_font(rendering.get_target_font_description())
            textview.get_pango_context().set_font_description(rendering.get_target_font_description())

    def _get_editing_start_pos(self, elem):
        if not elem:
            return 0
        translation_start = self.first_word_re.match(unicode(elem)).span()[1]
        start_elem = elem.elem_at_offset(translation_start)
        if not start_elem.iseditable:
            flattened = elem.flatten()
            start_index = flattened.index(start_elem)
            if start_index == len(flattened)-1:
                return len(elem)
            next_elem = flattened[start_index+1]
            return elem.elem_offset(next_elem)
        return translation_start

    def _get_widgets(self):
        """Get the widgets we would like to use from the loaded Glade XML object."""
        if not getattr(self, '_widgets', None):
            self._widgets = {}

        widget_names = ('vbox_editor', 'vbox_middle', 'vbox_sources', 'vbox_targets', 'vbox_options', 'vbox_right')

        for name in widget_names:
            self._widgets[name] = self.gui.get_widget(name)

        self._widgets['vbox_targets'].connect('key-press-event', self._on_key_press_event)

    def _set_menu_items_sensitive(self, sensitive=True):
        for widget in (self.mnu_next, self.mnu_prev, self.mnu_transfer):
            widget.set_sensitive(sensitive)

    def _update_editor_gui(self):
        """Build the default editor with the following components:
            - A C{gtk.TextView} for each source
            - A C{gtk.TextView} for each target
            - A C{ListNavigator} for the unit states
            - A C{gtk.Label} for programmer notes
            - A C{gtk.Label} for translator notes
            - A C{gtk.Label} for context info"""
        # We assume a unit exists, otherwise none of this makes sense:
        self._layout_update_notes('programmer')
        self._layout_update_sources()
        self._layout_update_context_info()
        self._layout_update_targets()
        self._layout_update_notes('translator')
        self._layout_update_states()
        self._set_menu_items_sensitive(True)

    def _update_textview_language(self, text_view, language):
        language = str(language)
        #logging.debug('Updating text view for language %s' % (language))
        text_view.get_pango_context().set_language(rendering.get_language(language))
        self.emit('textview-language-changed', text_view, language)


    # GUI BUILDING CODE #
    def _create_sources(self):
        for i in range(len(self.sources), self.MAX_SOURCES):
            source = self._create_textbox(u'', editable=False, role='source')
            textbox = source.get_child()
            textbox.modify_font(rendering.get_source_font_description())
            self._widgets['vbox_sources'].pack_start(source)
            self.sources.append(textbox)

            # The following fixes a very weird crash (bug #810)
            def ignore_tab(txtbx, event, eventname):
                if event.keyval in (gtk.keysyms.Tab, gtk.keysyms.ISO_Left_Tab):
                    self.focused_target_n = 0
                    return True
            textbox.connect('key-pressed', ignore_tab)

        self.emit('sources-created', self.sources)

    def _create_targets(self):
        def on_textbox_n_press_event(textbox, event, eventname):
            """Handle special keypresses in the textarea."""

        def target_key_press_event(textbox, event, eventname, next_textbox):
            if not eventname:
                return False
            if eventname in  ('enter', 'ctrl-enter', 'ctrl-shift-enter'):
                if next_textbox is not None and next_textbox.props.visible:
                    self.focus_text_view(next_textbox)
                else:
                    if eventname == 'ctrl-enter' and self.unit.STATE:
                        #Ctrl+Enter means additionally advance the unit in the workflow
                        listnav = self._widgets['state']
                        listnav.move_state(1)
                    elif eventname == 'ctrl-shift-enter' and self.unit.STATE:
                        listnav = self._widgets['state']
                        listnav.move_state(-1)
                    # textbox is the last text view in this unit, so we need to move on
                    # to the next one.
                    textbox.parent.parent.emit('key-press-event', event)
                return True

            # Alt-Down
            elif eventname == 'alt-down':
                idle_add(self.copy_original, textbox)
                return True

            # Shift-Tab
            elif eventname == 'shift-tab':
                if self.focused_target_n > 0:
                    self.focused_target_n -= 1
                return True
            # Ctrl-Tab
            elif eventname == 'ctrl-tab':
                self.controller.main_controller.lang_controller.view.focus()
                return True
            # Ctrl-Shift-Tab
            elif eventname == 'ctrl-shift-tab':
                self.controller.main_controller.mode_controller.view.focus()
                return True

            return False

        for i in range(len(self.targets), self.MAX_TARGETS):
            target = self._create_textbox(u'', editable=True, role='target', scroll_policy=gtk.POLICY_AUTOMATIC)
            textbox = target.get_child()
            textbox.modify_font(rendering.get_target_font_description())
            textbox.selector_textboxes = self.sources
            textbox.selector_textbox = self.sources[0]
            textbox.connect('paste-clipboard', self._on_textbox_paste_clipboard, i)
            textbox.connect('text-inserted', self._on_target_insert_text, i)
            textbox.connect('text-deleted', self._on_target_delete_range, i)
            textbox.connect('changed', self._on_target_changed, i)

            self._widgets['vbox_targets'].pack_start(target)
            self.targets.append(textbox)

        for target, next_target in zip(self.targets, self.targets[1:] + [None]):
            target.connect('key-pressed', target_key_press_event, next_target)

        self.emit('targets-created', self.targets)

    def _create_textbox(self, text=u'', editable=True, role=None, scroll_policy=gtk.POLICY_AUTOMATIC):
        textbox = TextBox(self.controller.main_controller, role=role)
        textbox.set_editable(editable)
        textbox.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        textbox.set_border_window_size(gtk.TEXT_WINDOW_TOP, 1)
        textbox.set_left_margin(2)
        textbox.set_right_margin(2)
        textbox.set_text(text or u'')
        textbox.connect('focus-in-event', self._on_textbox_focused)
        textbox.connect('focus-out-event', self._on_textbox_unfocused)

        scrollwnd = gtk.ScrolledWindow()
        scrollwnd.set_policy(gtk.POLICY_NEVER, scroll_policy)
        scrollwnd.set_shadow_type(gtk.SHADOW_IN)
        scrollwnd.add(textbox)

        return scrollwnd

    def _create_workflow_liststore(self):
        workflow = self.controller.current_unit._workflow
        lst = gtk.ListStore(str, object)
        if not workflow:
            return lst
        for state in workflow.states:
            lst.append([state.name, state])
        return lst

    def _layout_update_notes(self, origin):
        if origin not in self._widgets['notes']:
            label = gtk.Label()
            label.set_line_wrap(True)
            label.set_justify(gtk.JUSTIFY_FILL)
            label.set_property('selectable', True)

            self._widgets['vbox_middle'].pack_start(label)
            if origin == 'programmer':
                self._widgets['vbox_middle'].reorder_child(label, 0)
            elif origin == 'translator':
                self._widgets['vbox_middle'].reorder_child(label, 4)

            self._widgets['notes'][origin] = label

        note_text = self.unit.getnotes(origin) or u""

        if origin == "programmer" and len(note_text) < 15 and self.unit is not None and self.unit.getlocations():
            note_text += u"  " + u" ".join(self.unit.getlocations()[:3])

        # FIXME: This is a temporary quick fix (to bug 1145) to ensure that
        # excessive translator comments don't cover the whole display.
        # The labels used for displaying these comments (programmer- as well as
        # translator comments) should be displayed in a scrollable widget with
        # proper size limitations.
        TEXT_LIMIT = 200
        if origin == "translator" and len(note_text) > TEXT_LIMIT:
            note_text = note_text[:TEXT_LIMIT] + '...'

        self._widgets['notes'][origin].set_text(note_text)

        if note_text:
            self._widgets['notes'][origin].show_all()
        else:
            self._widgets['notes'][origin].hide()

    def _layout_update_sources(self):
        num_source_widgets = len(self.sources)

        if num_source_widgets < self.MAX_SOURCES:
            # Technically the condition above will only be True when num_target_widgets == 0, ie.
            # no target text boxes has been created yet.
            self._create_sources()
            num_source_widgets = len(self.sources)

        if self.unit is None:
            if num_source_widgets >= 1:
                # The above condition should *never* be False
                textbox = self.sources[0]
                textbox.set_text(u'')
                textbox.parent.show()
            for i in range(1, num_source_widgets):
                self.sources[i].parent.hide_all()
            return

        num_unit_sources = 1
        if self.unit.hasplural():
            num_unit_sources = len(self.unit.source.strings)

        for i in range(self.MAX_SOURCES):
            if i < num_unit_sources:
                sourcestr = self.unit.rich_source[i]
                self.sources[i].modify_font(rendering.get_source_font_description())
                # FIXME: This modfies the unit's copy - we should not do this
                self.sources[i].set_text(sourcestr)
                self.sources[i].parent.show_all()
                #logging.debug('Showing source #%d: %s' % (i, self.sources[i]))
            else:
                #logging.debug('Hiding source #%d: %s' % (i, self.sources[i]))
                self.sources[i].parent.hide_all()

    def _layout_update_context_info(self):
        if not self._widgets['context_info']:
            label = gtk.Label()
            label.set_line_wrap(True)
            label.set_justify(gtk.JUSTIFY_FILL)
            label.set_property('selectable', True)
            self._widgets['vbox_middle'].pack_start(label)
            self._widgets['vbox_middle'].reorder_child(label, 2)
            self._widgets['context_info'] = label

        if self.unit.getcontext():
            self._widgets['context_info'].show()
            self._widgets['context_info'].set_text(self.unit.getcontext() or u"")
        else:
            self._widgets['context_info'].hide()

    def _layout_update_targets(self):
        num_target_widgets = len(self.targets)

        if num_target_widgets < self.MAX_TARGETS:
            # Technically the condition above will only be True when num_target_widgets == 0, ie.
            # no target text boxes has been created yet.
            self._create_targets()
            num_target_widgets = len(self.targets)

        if self.unit is None:
            if num_target_widgets >= 1:
                # The above condition should *never* be False
                textbox = self.targets[0]
                textbox.set_text(u'')
                textbox.parent.show_all()
            for i in range(1, num_target_widgets):
                self.targets[i].parent.hide_all()
            return

        num_unit_targets = 1
        nplurals = 1
        if self.unit.hasplural():
            num_unit_targets = len(self.unit.target.strings)
            nplurals = self.controller.main_controller.lang_controller.target_lang.nplurals

        visible_sources = [src for src in self.sources if src.props.visible]

        rich_target = self.unit.rich_target
        rich_target_len = len(rich_target)
        for i in range(self.MAX_TARGETS):
            if i < nplurals:
                # plural forms already in file
                targetstr = u''
                if i < rich_target_len and rich_target[i] is not None:
                    targetstr = rich_target[i]
                self.targets[i].modify_font(rendering.get_target_font_description())
                self.targets[i].set_text(targetstr)
                self.targets[i].parent.show_all()
                self.targets[i].selector_textboxes = visible_sources
                self.targets[i].selector_textbox = visible_sources[0]
                #logging.debug('Showing target #%d: %s' % (i, self.targets[i]))
            else:
                # outside plural range
                #logging.debug('Hiding target #%d: %s' % (i, self.targets[i]))
                self.targets[i].parent.hide_all()

    def _layout_update_states(self):
        if not self._widgets['state'] and self.unit.STATE:
            statenav = ListNavigator()
            statenav.set_tooltips_text(
                _("Move one step back in the workflow (Ctrl+Shift+Enter)"), \
                _("Click to move to a specific state in the workflow"), \
                _("Move one step forward in the workflow (Ctrl+Enter)")
            )
            statenav.connect('selection-changed', self._on_state_changed)
            self._widgets['vbox_right'].pack_end(statenav, expand=False, fill=False)
            self._widgets['state'] = statenav

        state_names = self.controller.get_unit_state_names()
        if not state_names or not self.unit.STATE:
            widget = self._widgets['state']
            if widget:
                widget.hide()
            return
        state_name = state_names[self.unit.get_state_id()]

        unselectable = state_names.get(0, None)
        if unselectable:
            unselectable = [unselectable]

        self._widgets['state'].set_model(
            self._create_workflow_liststore(),
            unselectable=unselectable,
            select_name=state_name,
        )
        self._widgets['state'].show_all()

    def update_state(self, newstate):
        """Update it without emitting any signals or recreating anything."""
        self._widgets['state'].select_by_name(newstate)

    # EVENT HANLDERS #
    def _on_state_changed(self, listnav, newstate):
        if self.controller.current_unit._workflow:
            self.controller.set_current_state(newstate, from_user=True)
        self.modified()

    def _on_key_press_event(self, _widget, event, *_args):
        if event.keyval == gtk.keysyms.Return or event.keyval == gtk.keysyms.KP_Enter:
            self.must_advance = True
            # Clear selected elements
            self.editing_done()
            return True
        self.must_advance = False
        return False

    def _on_query_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        return True

    def _on_target_changed(self, buffer, index):
        tgt = self.targets[index]
        nplurals = self.controller.main_controller.lang_controller.target_lang.nplurals
        if tgt.elem is not None:
            rich_target = self.unit.rich_target
            if self.unit.hasplural() and len(rich_target) < nplurals:
                # pad the target with empty strings
                rich_target += (nplurals - len(rich_target)) * [u""]
            rich_target[index] = tgt.elem
            self.unit.rich_target = rich_target
        else:
            newtext = self.get_target_n(index)
            if self.unit.hasplural():
                # FIXME: The following two lines are necessary because self.unit.target always
                # returns a new multistring, so you can't assign to an index directly.
                target = self.unit.target.strings
                if len(target) < nplurals:
                    # pad the target with empty strings
                    target += (nplurals - len(target)) * [u""]
                target[index] = newtext
                self.unit.target = target
            elif index == 0:
                self.unit.target = newtext
            else:
                raise IndexError()

        self.modified()

    def _on_target_insert_text(self, textbox, ins_text, offset, elem, target_num):
        #logging.debug('emit("insert-text", ins_text="%s", offset=%d, elem=%s, target_num=%d)' % (ins_text, offset, repr(elem), target_num))
        self.emit('insert-text', ins_text, offset, elem, target_num)

    def _on_target_delete_range(self, textbox, deleted, parent, offset, cursor_pos, elem, target_num):
        #logging.debug('emit("delete-text", deleted=%s, offset=%d, cursor_pos=%d, elem=%s, target_num=%d)' % (deleted, offset, cursor_pos, repr(elem), target_num))
        self.emit('delete-text', deleted, parent, offset, cursor_pos, elem, target_num)

    def _on_textbox_paste_clipboard(self, textbox, target_num):
        buff = textbox.buffer
        old_text = textbox.get_text()
        ins_iter  = buff.get_iter_at_mark(buff.get_insert())
        selb_iter = buff.get_iter_at_mark(buff.get_selection_bound())

        offsets = {
            'insert_offset': ins_iter.get_offset(),
            'selection_offset': selb_iter.get_offset()
        }

        #logging.debug('emit("paste-start", old_text="%s", offsets=%s, target_num=%d)' % (old_text, offsets, target_num))
        self.emit('paste-start', old_text, offsets, target_num)

    def _on_textbox_focused(self, textbox, event):
        for mnu in (self.mnu_cut, self.mnu_copy, self.mnu_paste):
            mnu.set_sensitive(True)

    def _on_textbox_unfocused(self, textbox, event):
        for mnu in (self.mnu_cut, self.mnu_copy, self.mnu_paste):
            mnu.set_sensitive(False)
