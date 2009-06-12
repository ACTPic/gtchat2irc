#!/usr/bin/env python
"""
GT Chat to IRC Gateway

License: 3 clause BSD

In this file, the IRC server is instantiated and the
GTChat connection is established.
"""

import sys


sys.path.append("..")

from gtchatbridge import sirc


class GTChatConnection(object):
    def __init__(self, url):
        self.url = url
        self.rooms = {} # name -> set of names


class GTChatUser(sirc.DummyUser):
    def __init__(self, nick, ID, server):
        sirc.DummyUser.__init__(self, nick, ID)
        self.server = server
        self.init()

    def send(self, msg):
        m_user, m_cmd, m_self, m_message = (self.TranslateMessage(msg) + [""])[:4]
        m_cmd = m_cmd.lower()
        m_message = m_message[:-1]
        if m_cmd == 'privmsg':
            self.privmsg(m_user, msg, m_message)
        else:
            print "did not understand", msg

    def privmsg(self, user, rawmsg, msg):
        print user, "writes", msg 

    #self.data['away'] = reason

    def join(self, chan):
        chan = chan.strip()
        try:
            self.server.lock.acquire_lock()
            try:
                c = self.server.channels[chan]
            except KeyError:
                c = sirc.IRCChannel(self.server.host, chan)
                self.server.channels[chan] = c
                c.start()
        finally: self.server.lock.release_lock()
        #if c.isbanned(self): raise IRCException("You have been banned from this channel", 480, chan)
        c.add(self)
        self.server.chanserv.event_join(self, c)

    def IRC_part(self, chan):
            self.server.lock.acquire_lock()
            try:
                try:
                    c = self.server.channels[chan]
                except:
                    return
            finally:
                self.server.lock.release_lock()
    def _part(self, c):
        c.remove(self, True, reason)
        self.server.chanserv.event_part(self, c)
        if c.isempty():
            del self.server.channels[chan]

    def do_quit(self, reason):
        self.server.nickserv.event_leave(self)
        self.server.lock.acquire_lock()
        try:
            self.s.close()
            for chan in self.server.channels:
                self._part(chan)
            del self.server.nicks[self.data['nick']]
        finally:
            self.server.lock.release_lock()

    def init(self):
        self.data['user'] = "bridge"
        self.server.nicks[self.data['nick'].lower()] = self
        self.IRC_ID = "%s!~%s@%s" % (self.data['nick'], self.data['user'][0], "server")
        self.data['mode'] = ['i']
        self.server.nickserv.event_register(self)


import threading

class TestThread(threading.Thread):
    def __init__(self, a, b):
        self.a = a
        self.b = b
        threading.Thread.__init__(self)
    def run(self):
        import time
        time.sleep(10)
        self.a(self.b())



def run_on_port(port):
    s = sirc.IRCServer(('0.0.0.0', port), "localhost")
    a = GTChatUser("nick", "ID", s)
    TestThread(a.join, lambda: s.channels.items()[0][0]).start()
    print "\nListening on port %d" % port
    s.run()


if __name__ == "__main__":
    import random
    port = random.randint(2000, 10000)#6667
    run_on_port(port)

