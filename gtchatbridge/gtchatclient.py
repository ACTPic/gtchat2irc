#!/usr/bin/env python
import sys, os, re
import mechanize


sys.path.append("..")

from gtchatbridge import config

b = mechanize.Browser(
	factory=mechanize.DefaultFactory(i_want_broken_xhtml_support=True)
)
b.set_handle_robots(False)

b.open("http://www.psychose-chat.de")
b.follow_link(nr=0)
b.select_form(nr=0)

b["username"] = config.username 
b["password"] = config.password
b["room"] = [config.room]
b.submit()
res = b.follow_link(nr=0)
content = res.read()

idmatch = re.search(r'chat\.pl\?id=(\d+)"', content);
id = 0
if idmatch and idmatch.group(1):
	id = idmatch.group(1)

if not id:
	print "Login fehlgeschlagen."
	print content;
	exit()

print "Login erfolgreich, Session: id=" + id;

