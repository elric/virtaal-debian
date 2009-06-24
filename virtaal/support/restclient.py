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

import StringIO
import urllib
import logging

import gobject
import pycurl

from virtaal.common.gobjectwrapper import GObjectWrapper

class RESTClient(object):
    """Nonblocking client that can handle multiple HTTP REST requests"""

    class Request(GObjectWrapper):
        """Single HTTP REST request, blocking if used standalone"""
        __gtype_name__ = 'RestClientRequest'
        __gsignals__ = {
            "REST-success": (gobject.SIGNAL_RUN_LAST,
                             gobject.TYPE_NONE,
                             (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
            "REST-client-error": (gobject.SIGNAL_RUN_LAST,
                                  gobject.TYPE_NONE,
                                  (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
            "REST-server-error": (gobject.SIGNAL_RUN_LAST,
                                  gobject.TYPE_NONE,
                                  (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        }

        def __init__(self, url, id, method='GET', data=None, headers=None):
            GObjectWrapper.__init__(self)
            self.result = StringIO.StringIO()
            self.result_headers = StringIO.StringIO()

            # do we really need to keep these around?
            self.url = url.encode("utf-8")
            self.id = id.encode("utf-8")
            self.method = method
            self.data = data
            self.headers = headers
            self.status = None

            # the actual curl request object
            self.curl = pycurl.Curl()
            if (logging.root.level == logging.DEBUG):
                self.curl.setopt(pycurl.VERBOSE, 1)

            self.curl.setopt(pycurl.WRITEFUNCTION, self.result.write)
            self.curl.setopt(pycurl.HEADERFUNCTION, self.result_headers.write)
            self.curl.setopt(pycurl.URL, self.url + "/" + urllib.quote_plus(id))

            # let's set the HTTP request method
            if method == 'GET':
                self.curl.setopt(pycurl.HTTPGET, 1)
            elif method == 'POST':
                self.curl.setopt(pycurl.POST, 1)
            elif method == 'PUT':
                self.curl.setopt(pycurl.UPLOAD, 1)
            else:
                self.curl.setopt(pycurl.CUSTOMREQUEST, method)
            if data:
                if method == "PUT":
                    self.data = StringIO.StringIO(data)
                    self.curl.setopt(pycurl.READFUNCTION, self.data.read)
                    self.curl.setopt(pycurl.INFILESIZE, len(self.data.getvalue()))
                else:
                    self.curl.setopt(pycurl.POSTFIELDS, self.data)
                    self.curl.setopt(pycurl.POSTFIELDSIZE, len(self.data))
            if headers:
                self.curl.setopt(pycurl.HTTPHEADER, headers)

            # self reference required, because CurlMulti will only return
            # Curl handles
            self.curl.request = self


        def perform(self):
            """run the request (blocks)"""
            self.curl.perform()


        def handle_result(self):
            """called after http request is done"""
            self.status = self.curl.getinfo(pycurl.HTTP_CODE)

            #TODO: handle 3xx, throw exception on other codes
            if self.status >= 200 and self.status < 300:
                # 2xx indicated success
                self.emit("REST-success", self.id, self.result.getvalue())
            elif self.status >= 400 and self.status < 500:
                # 4xx client error
                self.emit("REST-client-error", self.id, self.status)
            elif self.status >= 500 and self.status < 600:
                # 5xx server error
                self.emit("REST-server-error", self.id, self.status)


    def __init__(self):
        # state variable used to add and remove dispatcher to gtk
        # event loop
        self.running = False

        # Since pycurl doesn't keep references to requests, requests
        # get garbage collected before they are done. We need  to keep requests in
        # a set and detroy them manually.
        self.requests = set()
        self.curl = pycurl.CurlMulti()


    def add(self,request):
        """add a request to the queue"""
        self.curl.add_handle(request.curl)
        self.requests.add(request)
        self.run()


    def run(self):
        """client should not be running when request queue is empty"""
        if self.running: return
        gobject.timeout_add(100, self.perform)
        self.running = True


    def close_request(self, handle):
        """finalize a successful request"""
        self.curl.remove_handle(handle)
        handle.request.handle_result()
        self.requests.remove(handle.request)


    def perform(self):
        """main event loop function, non blocking execution of all queued requests"""
        ret, num_handles = self.curl.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM and num_handles == 0:
            self.running = False
        num, completed, failed = self.curl.info_read()
        [self.close_request(com) for com in completed]
        #TODO: handle failed requests
        if not self.running:
            #we are done with this batch what do we do?
            return False
        return True
