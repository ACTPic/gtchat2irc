#!/usr/bin/env python
"""
GT Chat to IRC Gateway

License: 3 clause BSD

In this file, the IRC server is instantiated and the
GTChat connection is established.
"""

import sys


sys.path.append("..")

from gtchatbridge import sirc, config


class GTChatOutgoing(object):
    """ Interface """
    def message(self, txt):
        pass

    def set_away(self, txt):
        pass


class GTChatIncoming(object):
    def __init__(self, server, roomname):
        self.server = server
        self.roomname = roomname
        self.users = {} # nick -> GTChatUser()

        # init the empty channel
        self.channel = chan = "!" + roomname
        try:
            self.server.lock.acquire_lock()
            try:
                c = self.server.channels[chan]
            except KeyError:
                c = sirc.IRCChannel(self.server.host, chan)
                self.server.channels[chan] = c
                c.start()
        finally:
            self.server.lock.release_lock()

    def sanitize_nick(self, nick):
        return nick

    def join(self, nick, flags=()):
        self._get_user(nick).join(self.channel)

    def part(self, nick):
        self._get_user(nick).part(self.channel)
    quit = part

    def message(self, nick, msg): # XXX implement me
        pass

    def nickchange(self, old, new):
        user = _get_user(old)
        user.nick(new)

    def set_away(self, nick, away_status): # XXX not implemented
        pass

    def _get_user(self, nick):
        nick_sanitized = self.sanitize_nick(nick)
        IRC_ID = "%s!~%s@%s" % (nick_sanitized, 'webchatuser', 'somehost.invalid')
        user = self.users.setdefault(nick, GTChatUser(nick_sanitized, IRC_ID, self.server))
        return user


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
        try:
            self.server.lock.acquire_lock()
            try:
                c = self.server.channels[chan]
            except KeyError:
                c = sirc.IRCChannel(self.server.host, chan)
                self.server.channels[chan] = c
                c.start()
        finally: self.server.lock.release_lock()
        c.add(self)
        self.server.chanserv.event_join(self, c)

    def nick(self, nick):
        self.server.lock.acquire_lock()
        try:
            del self.server.nicks[self.data['nick'].lower()]
            self.data['nick'] = nick
            self.server.nicks[nick.lower()] = self
            # XXX send nick change message!
        finally:
            self.server.lock.release_lock()

    def part(self, chan):
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

    def quit(self, reason):
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
    def __init__(self, conn):
        self.conn = conn
        threading.Thread.__init__(self)

    def run(self):
        print "Simulating webchat"
        self.conn.join("rudi")

    def sendmsg(self, txt):
        print "Sending to webchat", txt


def run_on_port(port):
    s = sirc.IRCServer((config.listen_ip, port), "chat.invalid")
    print "\nListening on %s:%d" % (config.listen_ip, port)

    conn = GTChatOutgoing(s, config.room)
    t = TestThread(conn)
    s.run()


if __name__ == "__main__":
    import random
    port = random.randint(2000, 10000)#config.port
    run_on_port(port)

