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

import StringIO
import urllib
import logging

import gobject
import pycurl
import urllib

from virtaal.common.gobjectwrapper import GObjectWrapper

__all__ = ['HTTPClient', 'HTTPRequest', 'RESTRequest']


class HTTPRequest(GObjectWrapper):
    """Single HTTP request, blocking if used standalone."""

    __gtype_name__ = 'HttpClientRequest'
    __gsignals__ = {
        "http-success":      (gobject.SIGNAL_RUN_LAST, None, (object,)),
        "http-redirect":     (gobject.SIGNAL_RUN_LAST, None, (object,)),
        "http-client-error": (gobject.SIGNAL_RUN_LAST, None, (object,)),
        "http-server-error": (gobject.SIGNAL_RUN_LAST, None, (object,)),
    }

    def __init__(self, url, method='GET', data=None, headers=None,
            headers_only=False, user_agent=None, follow_location=False,
            force_quiet=True):
        GObjectWrapper.__init__(self)
        self.result = StringIO.StringIO()
        self.result_headers = StringIO.StringIO()

        if isinstance(url, unicode):
            self.url = url.encode("utf-8")
        else:
            self.url = url
        self.method = method
        self.data = data
        self.headers = headers
        self.status = None

        # the actual curl request object
        self.curl = pycurl.Curl()
        if (logging.root.level == logging.DEBUG and not force_quiet):
            self.curl.setopt(pycurl.VERBOSE, 1)

        self.curl.setopt(pycurl.WRITEFUNCTION, self.result.write)
        self.curl.setopt(pycurl.HEADERFUNCTION, self.result_headers.write)
        # We want to use gzip and deflate if possible:
        self.curl.setopt(pycurl.ENCODING, "") # use all available encodings
        self.curl.setopt(pycurl.URL, self.url)

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
        if headers_only:
            self.curl.setopt(pycurl.HEADER, 1)
            self.curl.setopt(pycurl.NOBODY, 1)
        if user_agent:
            self.curl.setopt(pycurl.USERAGENT, user_agent)
        if follow_location:
            self.curl.setopt(pycurl.FOLLOWLOCATION, 1)

        # Proxy: let's be careful to isolate the protocol to ensure that we
        # support the case where http and https might use different proxies
        split_url = self.url.split('://', 1)
        if len(split_url) > 1:
            #We were able to get a protocol
            protocol = split_url[0]
            proxies = urllib.getproxies()
            if protocol in proxies:
                self.curl.setopt(pycurl.PROXY, proxies[protocol])

            # On Windows urllib.getproxies() doesn't contain https if "Use the
            # same proxy for all protocols" is selected. So we might want to
            # guess that the http proxy is useful, but we have no way to know
            # if the https proxy is intentionally not specified. Environment
            # variables and separately specified (even if identical) settings
            # work as expected.
            # Possible code to reuse the http proxy for https:
#            elif protocol is 'https' and 'http' in proxies:
#                    self.curl.setopt(pycurl.PROXY, proxies['http'])

        # self reference required, because CurlMulti will only return
        # Curl handles
        self.curl.request = self

    def get_effective_url(self):
        return self.curl.getinfo(pycurl.EFFECTIVE_URL)

    def perform(self):
        """run the request (blocks)"""
        self.curl.perform()

    def handle_result(self):
        """called after http request is done"""
        self.status = self.curl.getinfo(pycurl.HTTP_CODE)

        #TODO: handle 3xx, throw exception on other codes
        if self.status >= 200 and self.status < 300:
            # 2xx indicated success
            self.emit("http-success", self.result.getvalue())
        elif self.status >= 300 and self.status < 400:
            # 3xx redirection
            self.emit("http-redirect", self.result.getvalue())
        elif self.status >= 400 and self.status < 500:
            # 4xx client error
            self.emit("http-client-error", self.status)
        elif self.status >= 500 and self.status < 600:
            # 5xx server error
            self.emit("http-server-error", self.status)


class RESTRequest(HTTPRequest):
    """Single HTTP REST request, blocking if used standalone."""

    def __init__(self, url, id, method='GET', data=None, headers=None, user_agent=None):
        super(RESTRequest, self).__init__(url, method, data, headers, user_agent=user_agent)

        url = self.url
        self.id = id
        if id:
            url += '/' + urllib.quote(id.encode('utf-8'), safe='')

        self.curl.setopt(pycurl.URL, url)


class HTTPClient(object):
    """Non-blocking client that can handle multiple (asynchronous) HTTP requests."""

    def __init__(self):
        # state variable used to add and remove dispatcher to gtk event loop
        self.running = False

        # Since pycurl doesn't keep references to requests, requests
        # get garbage collected before they are done. We need to keep requests in
        # a set and detroy them manually.
        self.requests = set()
        self.curl = pycurl.CurlMulti()
        self.user_agent = None

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

    def get(self, url, callback, etag=None, error_callback=None):
        headers = None
        if etag:
            # See http://en.wikipedia.org/wiki/HTTP_ETag for more details about ETags
            headers = ['If-None-Match: "%s"' % (etag)]
        request = HTTPRequest(url, headers=headers, user_agent=self.user_agent, follow_location=True)
        self.add(request)

        if callback:
            request.connect('http-success', callback)
            request.connect('http-redirect', callback)
        if error_callback:
            request.connect('http-client-error', error_callback)
            request.connect('http-server-error', error_callback)

    def set_virtaal_useragent(self):
        """Set a nice user agent indicating Virtaal and its version."""
        if self.user_agent and self.user_agent.startswith('Virtaal'):
            return
        import sys
        from virtaal.__version__ import ver as version
        platform = sys.platform
        if platform.startswith('linux'):
            import os
            # Debian, Ubuntu, Mandriva:
            if os.path.isfile('/etc/lsb-release'):
                try:
                    lines = open('/etc/lsb-release').read().splitlines()
                    for line in lines:
                        if line.startswith('DISTRIB_DESCRIPTION'):
                            distro = line.split('=')[-1]
                            distro = distro.replace('"', '')
                            platform = '%s; %s' % (platform, distro)
                except Exception, e:
                    pass
            # Fedora, RHEL:
            elif os.path.isfile('/etc/system-release'):
                try:
                    lines = open('/etc/system-release').read().splitlines()
                    for line in lines:
                        distro, dummy, distro_version, codename = line.split()
                        platform = '%s; %s %s' % (platform, distro, distro_version)
                except Exception, e:
                    pass
        elif platform.startswith('win'):
            major, minor = sys.getwindowsversion()[:2]
            # from http://msdn.microsoft.com/en-us/library/ms724833%28v=vs.85%29.aspx
            name_dict = {
                    (5, 0): "Windows 2000",
                    (5, 1): "Windows XP",
                    (6, 0): "Windows Vista", # Also Windows Server 2008
                    (6, 1): "Windows 7",     # Also Windows server 2008 R2
            }
            # (5, 2) includes XP Professional x64 Edition, Server 2003, Home Server, Server 2003 R2
            name = name_dict.get((major, minor), None)
            if name:
                platform = '%s; %s' % (platform, name)
        self.user_agent = 'Virtaal/%s (%s)' % (version, platform)
