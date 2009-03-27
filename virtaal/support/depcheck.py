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

__all__ = ['check_dependencies', 'extra_tests', 'import_checks']


# Modules to try and import:
import_checks = ['translate', 'gtk', 'gtk.glade', 'lxml.etree', 'simplejson', 'pycurl', 'sqlite3', 'wsgiref']


#########################
# Specific Module Tests #
#########################
def test_gtk_version():
    try:
        import gtk
        return gtk.ver >= (2, 12, 0)
    except Exception:
        pass
    return False

def test_sqlite3_version():
    try:
        import sqlite3
        return sqlite3.version_info >= (2, 3, 0)
    except Exception:
        pass
    return False

def test_translate_toolkit_version():
    try:
        from translate.__version__ import ver
        return ver >= (1, 3, 0)
    except Exception:
        pass
    return False


extra_tests = {
    'gtk': test_gtk_version,
    'sqlite3': test_sqlite3_version,
    'translate': test_translate_toolkit_version,
}


#############################
# General Testing Functions #
#############################
def test_import(modname):
    try:
        __import__(modname, globals(), [], [])
    except ImportError:
        return False
    return True

def check_dependencies(module_names=import_checks):
    """Returns a list of modules that could not be imported."""
    return [name for name in module_names if not test_import(name) or not extra_tests.get(name, lambda: True)()]



########
# MAIN #
########
if __name__ == '__main__':
    failed = check_dependencies()
    if not failed:
        print 'All dependencies met.'
    else:
        print 'Dependencies not met: %s' % (', '.join(failed))
