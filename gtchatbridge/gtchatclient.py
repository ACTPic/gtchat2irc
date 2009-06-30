#!/usr/bin/env python
import sys
import os
import re
import urllib
import urllib2
import asyncore
import httplib
import time
import threading
from StringIO import StringIO

import mechanize
from lxml import etree

sys.path.append("..")
from gtchatbridge import config, sirc


# generate opener manually to enforce HTTP 1.0
class HTTP10Connection(httplib.HTTPConnection):
    _http_vsn = 10
    _http_vsn_str = 'HTTP/1.0'

class HTTP10Handler(urllib2.AbstractHTTPHandler):
    def http10_open(self, req):
        return self.do_open(HTTP10Connection, req)

    http10_request = urllib2.AbstractHTTPHandler.do_request_

HTTP10Opener = urllib2.build_opener(HTTP10Handler)


class ChatParser(object):
    def __init__(self, chatconnector, gci):
        self.chatconnector = chatconnector
        self.gci = gci

    def parse_string(self, string):
        parser = etree.HTMLParser()
        if not string.strip():
            string = "<b></b>"
        tree = etree.parse(StringIO(string), parser)
        return tree

    def process_userlist(self, string):
        away_dict = {}
        tree = self.parse_string(string)
        row_elements = tree.xpath("/html/body/table/tr/td/table/tr[2]/td/table//tr")
        for elem in row_elements:
            nick = "".join(elem.itertext()).strip()
            away = False
            if nick[0] == "(" and nick[-1] == ")":
                nick = nick[1:-1]
                away = True
            away_dict[nick] = away
        return away_dict

    def process_tree(self, tree):
        script_elements = tree.xpath("//script")
        for s_elem in script_elements:
            txt = s_elem.text # we assume that only one function is called
            s_elem.getparent().remove(s_elem)
            if "updateUserList" in txt:
                self.chatconnector.update_userlist(self.process_userlist)
            elif (txt.strip().startswith('cgi="') or not txt.strip()
                    or "doLogin()" in txt or "updateRoomList" in txt):
                continue
            else:
                print "Unrecognized script tag", txt

        for font_elem in tree.xpath("//font[b/a[substring(@onclick, 1, 10) = 'insertText']]"):
            a_elem = font_elem.xpath("b/a")[0]
            match = re.search("/msg ([^ ]*) ", a_elem.attrib["onclick"])
            if not match:
                print "Unrecognized a tag", etree.tostring(a_elem)
                continue
            nick = match.groups()[0].encode("utf-8")
            txt_segments = list(font_elem.itertext())
            msg = ""
            is_private = False
            if "(zu" in txt_segments[1]:
                msg = txt_segments[1].replace(" (zu ", "")[:-2] + ": "
            elif "(privat" in txt_segments[1]:
                is_private = True
            elif ":" == txt_segments[1]:
                pass
            elif u' (fl\xfcstert an ' in txt_segments[1]:
                continue
            else:
                print "Unrecognized message mode: ", txt_segments
                continue
            msg += "".join(txt_segments[2:]).strip()
            self.gci.message(nick, msg, [None, True][is_private])
            font_elem.getparent().remove(font_elem)

        spare_segments = list(tree.getroot().itertext())
        if spare_segments:
            if (len(spare_segments) < 4 and spare_segments[0].strip() == "["
                    and spare_segments[-1].strip()[-1] == "]"):
                msg = spare_segments[2].strip()
                if "?" in msg:
                    src_nick, target_nick = msg[:-1].split("?", 1)
                    src_nick = src_nick.strip()
                    target_nick = target_nick.strip()
                    if target_nick and target_nick[-1] == "!":
                        target_nick = target_nick[:-1]
                        assert " " not in target_nick and " " not in src_nick
                        self.gci.nickchange(src_nick, target_nick)
                        return
                    # not a nick change
                if "ist jetzt weg" in msg:
                    msg_parts = msg.split("ist jetzt weg")
                    if msg_parts[1][0] == ":":
                        away_msg = msg_parts[1][1:-1].strip()
                    else:
                        away_msg = ""
                    nick = msg_parts[0].strip()
                    self.gci.set_away(nick, away_msg)
                    return
                elif "ist wieder da" in msg:
                    msg_parts = msg.split("ist wieder da")
                    nick = msg_parts[0].strip()
                    self.gci.set_away(nick, None)
                    return
                elif msg.startswith(">>>") or msg.startswith("<<<"):
                    return
            # XXX missing: recognise other messages
            self.gci.notice("Unparsed text: " + str(spare_segments))
            # " in tree ", etree.tostring(tree)


class ChatDispatcher(asyncore.file_dispatcher):
    def set_idletask(self, idletask):
        self.idletask = idletask

    def set_chatparser(self, chatparser):
        self.chatparser = chatparser

    def handle_read(self):
        data = self.recv(16 * 1024)
        #print "DATA FROM CHAT: ", data # XXX debugging
        try:
            self.chatparser.process_tree(self.chatparser.parse_string(data))
        except:
            import pdb
            if hasattr(pdb, "xpm"):
                pdb.xpm()
            else:
                import traceback
                traceback.print_exc()

    def handle_write(self):
        if not hasattr(self, "lastwrite"):
            self.lastwrite = 0
        if time.time() - self.lastwrite > 10:
            self.idletask()
            self.lastwrite = time.time()
        time.sleep(0.1)

    def handle_close(self):
        try:
            self.close()
        except OSError:
            pass
        print "Verbindung geschlossen"


class GTChatConnector(threading.Thread):
    def __init__(self, gci):
        threading.Thread.__init__(self)
        self.browser = mechanize.Browser(
            factory=mechanize.DefaultFactory(i_want_broken_xhtml_support=True)
        )
        self.browser.set_handle_robots(False)

        self.do_quit = False
        self.gci = gci
        self.users = set()

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
        data_socket = data_socket_urlobj.fp._sock.fp._sock.fileno()

        dispatcher = ChatDispatcher(data_socket)
        dispatcher.set_chatparser(ChatParser(self, self.gci))
        dispatcher.set_idletask(self.idle_task)
        asyncore.loop()

    def run(self):
        while not self.do_quit:
            self.login()
            self.read_data()
            # self.do_quit = True # for debugging
            print "Disconnected, logging in again ..."
            time.sleep(30)

    def update_userlist(self, parse_func):
        url = config.url + "?id=%s&action=userlist" % self.session_id
        page = urllib2.urlopen(url).read()
        away_dict = parse_func(page)
        away_dict = dict((k.encode("utf-8"), v) for k, v in away_dict.items())

        new_set = set(away_dict.keys())
        joining_users = new_set - self.users
        parting_users = self.users - new_set
        for user in joining_users:
            try:
                self.gci.join(user)
            except sirc.IRCException:
                pass
        for user in parting_users:
            self.gci.part(user)
        for user, status in away_dict.items():
            self.gci.set_away(user, [None, "XXX Unknown"][status]) # XXX
        self.users = new_set

    def idle_task(self):
        self.send_line("/alive")

    def send_line(self, line):
        url = config.url + "?id=%s&action=send" % self.session_id
        page = urllib2.urlopen(url, urllib.urlencode(dict(text=line))).read()
        #print "send line return page is", page

    # ----- Callback functions from the main module
    def message(self, txt, dest=None): # None -> current channel, otherwise nick
        try:
            txt.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            txt = txt.decode("utf-8").encode("latin-1")

        line = ""
        if dest is not None:
            try:
                dest.decode("utf-8")
            except UnicodeDecodeError:
                pass
            else:
                dest = dest.decode("utf-8").encode("latin-1")
            line += "/msg %s " % dest
        line += txt + "\x01"
        self.send_line(line)

    def set_away(self, txt):
        if txt is not None:
            self.send_line("/away " + txt)

    def change_nick(self, newnick):
        self.send_line("/nick " + newnick)


if __name__ == '__main__':
    GTChatConnector(None).run()

