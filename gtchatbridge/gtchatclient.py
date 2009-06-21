#!/usr/bin/env python
import sys
import os
import re
import urllib2
import asyncore
import httplib
import time
from StringIO import StringIO

import mechanize
from lxml import etree

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
        data = self.recv(16 * 1024)
        print "DATA FROM CHAT: ", data
        self.process_string(data)

    def process_string(self, string):
        parser = etree.HTMLParser()
        try:
            tree = etree.parse(StringIO(string), parser)
        except:
            import pdb; pdb.xpm()
        self.process_tree(tree)

    def process_tree(self, tree):
        script_elements = tree.xpath("(/html/body|/html/head)/script")
        for s_elem in script_elements:
            txt = s_elem.text # we assume that only one function is called
            if "updateUserList" in txt:
                print "UPDATE USER LIST"
            elif txt.strip().startswith('cgi="') or not txt.strip():
                continue
            else:
                print "Unrecognized script tag", etree.tostring(txt)

        for font_elem in tree.xpath("//font[b/a[substring(@onclick, 1, 10) = 'insertText']]"):
            a_elem = font_elem.xpath("b/a")[0]
            match = re.search("/msg ([^ ]*) ", a_elem.attrib["onclick"])
            if not match:
                print "Unrecognized a tag", etree.tostring(a)
                continue
            nick = match.groups()[0]
            txt_segments = list(font_elem.itertext())
            msg = ""
            is_private = False
            if "(zu" in txt_segments[1]:
                msg = txt_segments[1].replace(" (zu ", "")[:-2] + ":"
            elif "(privat" in txt_segments[1]:
                is_private = True
            elif ":" == txt_segments[1]:
                pass
            else:
                print "Unrecognized message mode: ", txt_segments
                continue
            msg += "".join(txt_segments[2:])
            print "%s Message by %s: %s" % (["", "private"][is_private], nick, msg)


    def handle_write(self):
        pass

    def handle_close(self):
        try:
            self.close()
        except OSError:
            pass
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
        data_url = config.url.replace("http://", "http10://") + "?id=%s&action=receive&dhtml=0" % self.session_id
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


if __name__ == '__main__':
    test_data = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">\n<html><body><font color="#00bb00"><b><a href="javascript:insertText(\'/msg xorEaxEax \')" onclick="insertText(\'/msg xorEaxEax \');return false;" style="color:#00bb00">xorEaxEax</a> (zu gwtest):</b> test</font></body></html>'
    #ChatDispatcher(sys.stdin).process_string(test_data)
    GTChatConnector().run()

