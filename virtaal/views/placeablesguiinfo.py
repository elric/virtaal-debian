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
import pango
from translate.storage.placeables import base, StringElem, general


class StringElemGUI(object):
    """
    A convenient container for all GUI properties of a L{StringElem}.
    """

    # MEMBERS #
    fg = '#000000'
    """The current foreground colour."""
    bg = '#ffffff'
    """The current background colour."""

    cursor_allowed = True
    """Whether the cursor is allowed to enter this element."""


    # INITIALIZERS #
    def __init__(self, elem, textbox, **kwargs):
        if not isinstance(elem, StringElem):
            raise ValueError('"elem" parameter must be a StringElem.')
        self.elem = elem
        self.textbox = textbox
        self.widgets = []
        self.create_repr_widgets()

        attribs = ('fg', 'bg', 'cursor_allowed')
        for kw in kwargs:
            if kw in attribs:
                setattr(self, kw, kwargs[kw])

    # METHODS #
    def create_tags(self):
        tag = gtk.TextTag()
        if self.fg:
            tag.props.foreground = self.fg

        if self.bg:
            tag.props.background = self.bg

        return [(tag, None, None)]

    def create_repr_widgets(self):
        """Creates the two widgets that are rendered before and after the
            contained string. The widgets should be placed in C{self.widgets}."""
        return None

    def copy(self):
        return self.__class__(
            elem=self.elem, textbox=self.textbox,
            fg=self.fg, bg=self.bg,
            cursor_allowed=self.cursor_allowed
        )

    def elem_at_offset(self, offset):
        """Find the C{StringElem} at the given offset.
            This method is used in Virtaal as a replacement for
            C{StringElem.elem_at_offset}, because this method takes the rendered
            widgets into account."""
        if offset < 0 or offset > self.length():
            return None

        pre_len = (self.widgets and self.widgets[0]) and 1 or 0

        # First check if offset doesn't point to a widget that does not belong to self.elem
        if self.textbox.buffer.get_iter_at_offset(offset).get_child_anchor() is not None and pre_len == 0:
            return None

        if self.elem.isleaf():
            return self.elem

        childlen = 0
        for child in self.elem.sub:
            if isinstance(child, StringElem):
                if not hasattr(child, 'gui_info'):
                    child.gui_info = self.textbox.placeables_controller.get_gui_info(child)(elem=child, textbox=self.textbox)

                elem = child.gui_info.elem_at_offset(offset - (pre_len+childlen))
                if elem:
                    return elem
                childlen += child.gui_info.length()
            else:
                if offset <= len(child):
                    return self.elem
                childlen += len(child)
        return None

    def get_insert_widget(self):
        return None

    def gui_to_tree_index(self, index):
        #elem = self.elem_at_offset(index)
        #gui_index = self.index(elem)
        #tree_index = self.elem.elem_offset(elem)
        #converted = tree_index + (index - gui_index)
        #if hasattr(elem, 'gui_info') and elem.gui_info.widgets and elem.gui_info.widgets[0]:
        #    converted -= 1
        #return converted

        # Let's try a different approach: The difference between a GUI offset and a tree offset is
        # the iter-consuming widgets in the text box. So we just iterate from the start of the text
        # buffer and count the positions without widgets.
        i = 0
        itr = self.textbox.buffer.get_start_iter()
        while itr.get_offset() < index:
            if itr.get_child_anchor() is None:
                i += 1
            itr.set_offset(itr.get_offset()+1)
        return i

    def index(self, elem):
        """Replacement for C{StringElem.elem_offset()} to be aware of included
            widgets."""
        if elem is self.elem:
            return 0

        i = 0
        for child in self.elem.sub:
            if isinstance(child, StringElem):
                index = child.gui_info.index(elem)
                if index >= 0:
                    return index + i
                i += child.gui_info.length()
            else:
                i += len(child)
        return -1

    def length(self):
        """Calculate the length of the current element, taking into account
            possibly included widgets."""
        length = len([w for w in self.widgets if w is not None])
        for child in self.elem.sub:
            if isinstance(child, StringElem):
                length += child.gui_info.length()
            else:
                length += len(child)
        return length

    def render(self, offset=-1):
        """Render the string element string and its associatd widgets."""
        buffer = self.textbox.buffer
        if offset < 0:
            offset = 0
            buffer.set_text('')

        if len(self.widgets) >= 1 and self.widgets[0]:
            anchor = buffer.create_child_anchor(buffer.get_iter_at_offset(offset))
            self.textbox.add_child_at_anchor(self.widgets[0], anchor)
            self.widgets[0].show()
            offset += 1

        for child in self.elem.sub:
            if isinstance(child, StringElem):
                child.gui_info.render(offset)
                offset += child.gui_info.length()
            else:
                buffer.insert(buffer.get_iter_at_offset(offset), child)
                offset += len(child)

        if len(self.widgets) >= 2:
            anchor = buffer.create_child_anchor(buffer.get_iter_at_offset(offset))
            self.textbox.add_child_at_anchor(self.widgets[1], anchor)
            self.widgets[1].show()
            offset += 1

        return offset

    def tree_to_gui_index(self, index):
        elem = self.elem.elem_at_offset(index)
        gui_index = self.index(elem)
        tree_index = self.elem.elem_offset(elem)
        converted = gui_index - (index - tree_index)
        if hasattr(elem, 'gui_info') and elem.gui_info.widgets and elem.gui_info.widgets[0]:
            converted += 1
        return converted


class PhGUI(StringElemGUI):
    fg = 'darkred'
    bg = '#f7f7f7'

class UrlGUI(StringElemGUI):
    fg = '#0000ff'
    bg = '#ffffff'

    def create_tags(self):
        tag = gtk.TextTag()
        tag.props.foreground = self.fg
        tag.props.background = self.bg
        tag.props.underline = pango.UNDERLINE_SINGLE
        return [(tag, None, None)]


class GPlaceableGUI(StringElemGUI):
    fg = '#f7f7f7'
    bg = 'darkred'

    def create_tags(self):
        metatag = gtk.TextTag()
        metatag.props.foreground = self.fg
        metatag.props.background = self.bg

        ttag = gtk.TextTag()
        ttag.props.foreground = StringElemGUI.fg
        ttag.props.background = 'yellow'

        prefixlen = len(self.get_prefix())
        return [
            (metatag, 0, -1),
            (ttag, prefixlen, -2),
        ]


class XPlaceableGUI(StringElemGUI):
    fg = '#ffffff'
    bg = '#000000'


element_gui_map = [
    (general.UrlPlaceable, UrlGUI),
    (general.EmailPlaceable, UrlGUI),
    (base.Ph, PhGUI),
    (base.G, GPlaceableGUI),
    (base.X, XPlaceableGUI),
]
