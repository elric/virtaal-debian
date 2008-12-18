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

from translate.services import opentranclient
from translate.search.lshtein import LevenshteinComparer

from virtaal.models import BaseModel
from virtaal.common import pan_app


class TMModel(BaseModel):
    """This is the translation memory model."""

    __gtype_name__ = 'OpenTranTMModel'
    __gsignals__ = {
        'match-found': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (gobject.TYPE_STRING, gobject.TYPE_PYOBJECT,))
    }

    # INITIALIZERS #
    def __init__(self, controller):
        super(TMModel, self).__init__()

        self.controller = controller
        self.comparer = LevenshteinComparer()

        language = pan_app.settings.language["contentlang"]
        #TODO: open-tran connection settings should come from configs
        self.tmclient = opentranclient.OpenTranClient("http://open-tran.eu/RPC2", language)
        self.cache = {}

        self.controller.connect('start-query', self.query)


    # METHODS #
    def query(self, tmcontroller, query_str):
        if self.cache.has_key(query_str):
            self.controller.accept_response(query_str, self.cache[query_str])
        else:
            self.tmclient.translate_unit(query_str, self.handle_matches)

    def handle_matches(self, widget, query_str, matches):
        #open-tran often gives too many results with many which can't really be
        #considered to be suitable for translation memory
        #TODO: we should probably parameterise these:
        #   (number of suggestions, minimum similarity)
        matches = matches[:20]
        for match in matches:
            match['quality'] = self.comparer.similarity(query_str, match['source'])
        # This use of .sort() is not compatible with Python 2.3
        matches.sort(key=lambda match: match['quality'], reverse=True)
        matches = matches[:3]
        self.cache[query_str] = matches
        self.emit('match-found', query_str, matches)
