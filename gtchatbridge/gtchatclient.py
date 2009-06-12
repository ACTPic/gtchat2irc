#!/usr/bin/env python
import sys, os, re
import mechanize

username = "gwtest"
password = "fnord"
room = "Ruheraum"

b = mechanize.Browser(
	factory=mechanize.DefaultFactory(i_want_broken_xhtml_support=True)
)
b.set_handle_robots(False)

b.open("http://www.psychose-chat.de")
b.follow_link(nr=0)
b.select_form(nr=0)
b["username"] = username 
b["password"] = password
b["room"] = [room]
b.submit()
res = b.follow_link(nr=0)
content = res.read()

if not re.search(r'"chat\.js"', content):
	print "Login fehlgeschlagen."
	print content;
	exit()

print "Login erfolgreich."
print content; 

