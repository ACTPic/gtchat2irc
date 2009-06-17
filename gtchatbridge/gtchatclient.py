#!/usr/bin/env python
import sys
import os
import re
import urllib2
import asyncore

import mechanize


sys.path.append("..")

from gtchatbridge import config


b = mechanize.Browser(
    factory=mechanize.DefaultFactory(i_want_broken_xhtml_support=True)
)
b.set_handle_robots(False)
b.open(config.url)
#b.follow_link(nr=0)
b.select_form(nr=0)

b["username"] = config.username 
b["password"] = config.password
b["room"] = [config.room]
b.submit()
res = b.follow_link(nr=0)
content = res.read()

idmatch = re.search(r'chat\.pl\?id=(\d+)"', content)
id = 0
if idmatch and idmatch.group(1):
	id = idmatch.group(1)

if not id:
    print "Login fehlgeschlagen." # XXX exception klasse erstellen
    print content
    exit()

print "Login erfolgreich, Session: id=" + id

data_url = config.url + "?id=%s&action=receive&dhtml=0" # XXX does not work, why? (cookies?)
data_socket_urlobj = urllib2.urlopen(data_url)
data_socket = data_socket_urlobj.fp._sock.fp._sock

class ChatDispatcher(asyncore.file_dispatcher):
    def handle_read(self):
        print "DATA FROM CHAT: ", self.recv(100)

    def handle_write(self):
        pass

    def handle_close(self):
        self.close()

dispatcher = ChatDispatcher(data_socket)
asyncore.loop()
