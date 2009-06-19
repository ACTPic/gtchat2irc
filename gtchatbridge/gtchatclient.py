#!/usr/bin/env python
import sys
import os
import re
import urllib2
import asyncore
import httplib
import time

import mechanize


sys.path.append("..")

from gtchatbridge import config


# generate opener manually to enforce HTTP 1.0
class HTTP10Connection(httplib.HTTPConnection):
    _http_vsn = 10
    _http_vsn_str = 'HTTP/1.0'

class HTTP10Handler(urllib2.AbstractHTTPHandler):
    def http10_open(self, req):
        return self.do_open(HTTP10Connection, req)

    http10_request = urllib2.AbstractHTTPHandler.do_request_

HTTP10Opener = urllib2.build_opener(HTTP10Handler)


class ChatDispatcher(asyncore.file_dispatcher):
    def set_chatconnector(self, connector):
        self.connector = connector

    def handle_read(self):
        print "DATA FROM CHAT: ", self.recv(16 * 1024)

    def handle_write(self):
        pass

    def handle_close(self):
        self.close()
        print "Verbindung geschlossen"


class GTChatConnector:
    def __init__(self):
        self.browser = mechanize.Browser(
            factory=mechanize.DefaultFactory(i_want_broken_xhtml_support=True)
        )
        self.browser.set_handle_robots(False)
        self.do_quit = False

    def login(self):
        b = self.browser
        b.open(config.url)
        b.select_form(nr=0)

        b["username"] = config.username
        b["password"] = config.password
        b["room"] = [config.room]
        b.submit()
        res = b.follow_link(nr=0)
        content = res.read()

        idmatch = re.search(r'chat\.pl\?id=(\d+)"', content)
        if idmatch and idmatch.group(1):
            session_id = idmatch.group(1)
        else:
            session_id = None
        self.session_id = session_id

        if not session_id:
            print content
            raise Exception("Login failed.") # XXX exception klasse erstellen

    def read_data(self):
        data_url = config.url.replace("http://", "http10://") + "?id=%s&action=receive&dhtml=0" % session_id
        data_socket_urlobj = HTTP10Opener.open(data_url)
        data_socket = data_socket_urlobj.fp._sock.fp._sock

        dispatcher = ChatDispatcher(data_socket)
        dispatcher.set_chatconnector(self)
        asyncore.loop()

    def run(self):
        self.login()
        while not self.do_quit:
            self.read_data()
            time.sleep(10)

