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

from test_scaffolding import TestScaffolding


class TestCursor(TestScaffolding):
    def test_move(self):
        self.store_controller.open_file(self.testfile[1])
        cursor = self.store_controller.cursor
        oldpos = cursor.pos
        cursor.move(1)
        assert cursor.pos == oldpos + 1
        cursor.move(-2)
        assert cursor.pos == len(cursor.indices) - 1

    def test_indices(self):
        cursor = self.store_controller.cursor
        cursor.pos = 0
        cursor.indices = [1, 2]
        assert cursor.pos == 0
        cursor.move(2)
        assert cursor.pos == 0
