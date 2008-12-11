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


class BasePlugin(object):
    """The base interface to be implemented by all plug-ins."""
    name = ''
    """The plug-in's name, suitable for display."""
    version = 0
    """The plug-in's version number."""

    def __new__(cls, *args, **kwargs):
        """Create a new plug-in instance and check that it is valid."""
        if not cls.name:
            raise Exception('No name specified')
        if cls.version <= 0:
            raise Exception('Invalid version number specified')
        return super(BasePlugin, cls).__new__(cls, *args, **kwargs)

    def __init__(self):
        raise NotImplementedError('This interface cannot be instantiated.')
