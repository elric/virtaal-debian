#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008 Zuza Software Foundation
#
# This file is part of Translate.
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

import os
import xmlrpclib
import logging

import pycurl

from translate.lang import data
from translate.search.lshtein import LevenshteinComparer

from virtaal.support import restclient

class OpenTranClient(restclient.RESTClient):
    """CRUD operations for TM units and stores"""

    def __init__(self, url, max_candidates=3, min_similarity=75, max_length=1000):
        restclient.RESTClient.__init__(self)

        self.max_candidates = max_candidates
        self.min_similarity = min_similarity
        self.comparer = LevenshteinComparer(max_length)

        self.url = url

        self.source_lang = None
        self.target_lang = None
        #detect supported language


    def translate_unit(self, unit_source, callback=None):
        if self.source_lang is None or self.target_lang is None:
            return
        if isinstance(unit_source, unicode):
            unit_source = unit_source.encode("utf-8")

        request_body = xmlrpclib.dumps(
            (unit_source, self.source_lang, self.target_lang), "suggest2")
        request = restclient.RESTClient.Request(
                self.url, unit_source, "POST", request_body)
        request.curl.setopt(pycurl.URL, self.url)
        self.add(request)
        if callback:
            request.connect("REST-success",
                            lambda widget, id, response: callback(widget, id, self.format_suggestions(id, response)))

    def lang_negotiate(self, language, callback):
        request_body = xmlrpclib.dumps((language,), "supported")
        request = restclient.RESTClient.Request(
            self.url, language, "POST", request_body)
        request.curl.setopt(pycurl.URL, self.url)
        self.add(request)
        request.connect("REST-success", callback)

    def set_source_lang(self, language):
        self.source_lang = None
        self.lang_negotiate(language, self._handle_source_lang)

    def set_target_lang(self, language):
        self.target_lang = None
        self.lang_negotiate(language, self._handle_target_lang)

    def _handle_target_lang(self, request, language, response):
        (result,), fish = xmlrpclib.loads(response)
        if result:
            self.target_lang = language
            logging.debug("target language %s supported" % language)
        else:
            lang = data.simplercode(language)
            if lang:
                self.lang_negotiate(lang, self._handle_target_lang)
            else:
                # language not supported
                self.source_lang = None
                logging.debug("target language %s not supported" % language)

    def _handle_source_lang(self, request, language, response):
        (result,), fish = xmlrpclib.loads(response)
        if result:
            self.source_lang = language
            logging.debug("source language %s supported" % language)
        else:
            lang = data.simplercode(language)
            if lang:
                self.lang_negotiate(lang, self._handle_source_lang)
            else:
                self.source_lang = None
                logging.debug("source language %s not supported" % language)

    def format_suggestions(self, id, response):
        """clean up open tran suggestion and use the same format as tmserver"""
        (suggestions,), fish = xmlrpclib.loads(response)
        results = []
        for suggestion in suggestions:
            result = {}
            result['target'] = suggestion['text']
            if isinstance(result['target'], unicode):
                result['target'] = result['target'].encode("utf-8")
            result['source'] = suggestion['projects'][0]['orig_phrase']
            #check for fuzzyness at the 'flag' member:
            for project in suggestion['projects']:
                if project['flags'] == 0:
                    break
            else:
                continue
            if isinstance(result['source'], unicode):
                result['source'] = result['source'].encode("utf-8")
            #open-tran often gives too many results with many which can't really be
            #considered to be suitable for translation memory
            result['quality'] = self.comparer.similarity(id, result['source'], self.min_similarity)
            if result['quality'] >= self.min_similarity:
                results.append(result)
        results.sort(key=lambda match: match['quality'], reverse=True)
        results = results[:self.max_candidates]
        return results
