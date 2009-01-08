#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2007-2009 Zuza Software Foundation
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

import re


# We want to draw unexpected spaces specially so that users can spot them
# easily without having to resort to showing all spaces weirdly

fancy_spaces_re = re.compile(r"""(?m)  #Multiline expression
        [ ]{2,}|     #More than two consecutive
        ^[ ]+|       #At start of a line
        [ ]+$        #At end of line""", re.VERBOSE)
"""A regular expression object to find all unusual spaces we want to show"""

def _fancyspaces(string):
    """Indicate the fancy spaces with a grey squigly."""
    spaces = string.group()
#    while spaces[0] in "\t\n\r":
#        spaces = spaces[1:]
    return u'<span underline="error" foreground="grey">%s</span>' % spaces


# Highligting for XML

xml_re = re.compile("&lt;[^>]+>")
def fancy_xml(escape):
    """Marks up the XML to appear dard red."""
    return u'<span foreground="darkred">%s</span>' % escape.group()


# Highlighting for escapes

def _fancyescape_n(escape):
    """Marks up the given escape to appear purple with a newline appended for
    the sake of wrapping."""
    return u'<span foreground="purple">%s</span>\n' % escape

def _fancyescape(escape):
    """Marks up the given escape to appear purple without a newline appended."""
    return u'<span foreground="purple">%s</span>' % escape


# Public methods

def markuptext(text, fancyspaces=True, markupescapes=True):
    """Markup the given text to be pretty Pango markup.

    Special characters (&, <) are converted, XML markup highligthed with
    escapes and unusual spaces optionally being indicated."""
    if not text:
        return ""
    text = text.replace(u"&", u"&amp;") # Must be done first!
    text = text.replace(u"<", u"&lt;")
    text = xml_re.sub(fancy_xml, text)

    if fancyspaces:
        text = fancy_spaces_re.sub(_fancyspaces, text)

    if markupescapes:
#        text = text.replace("\\", _fancyescape(r'\\'))
        text = text.replace(u"\r\n", _fancyescape_n(ur'\r\n'))
        text = text.replace(u"\n", _fancyescape_n(ur'\n'))
        text = text.replace(u"\r", _fancyescape_n(ur'\r'))
        text = text.replace(u"\t", _fancyescape(ur'\t'))
        # we don't need it at the end of the string
        if text.endswith(u"\n"):
            text = text[:-1]
    return text

def escape(text):
    """This is to escape text for use with gtk.TextView"""
    if not text:
        return ""
    text = text.replace("\\", '\\\\')
    text = text.replace("\n", '\\n\n')
    text = text.replace("\r", '\\r\n')
    text = text.replace("\\r\n\\n",'\\r\\n')
    text = text.replace("\t", '\\t')
    if text.endswith("\n"):
        text = text[:-len("\n")]
    return text

def unescape(text):
    """This is to unescape text for use with gtk.TextView"""
    if not text:
        return ""
    text = text.replace("\t", "")
    text = text.replace("\n", "")
    text = text.replace("\r", "")
    text = text.replace("\\t", "\t")
    text = text.replace("\\n", "\n")
    text = text.replace("\\r", "\r")
    text = text.replace("\\\\", "\\")
    return text
