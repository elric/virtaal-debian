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

from gtk import glade

from virtaal import pan_app


class BaseView(object):
    """Interface for views."""

    def __init__(self):
        raise NotImplementedError('This interface cannot be instantiated.')

    @classmethod
    def load_glade_file(cls, path_parts, root=None, domain=''):
        gladename = pan_app.get_abs_data_filename(path_parts)
        gui = glade.XML(gladename, root=root, domain=domain)
        return gladename, gui

    def show(self):
        raise NotImplementedError('This method needs to be implemented by all sub-classes.')
