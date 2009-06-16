#!/usr/bin/env python
"""
GT Chat to IRC Gateway

License: 3 clause BSD

In this file, the IRC server is instantiated and the
GTChat connection is established.

TODO:
    * ...
"""

import sys


sys.path.append("..")

from gtchatbridge import sirc, config


class GTChatOutgoingInterface(object):
    """ Interface """
    def message(self, txt, dest=None): # None -> current channel, otherwise nick
        pass

    def set_away(self, txt):
        pass


class GTChatIncoming(object):
    def __init__(self, server, roomname, outgoing_proxy=None):
        self.server = server
        self.roomname = roomname
        self.users = {} # nick -> GTChatUser()
        self.outgoing_proxy = outgoing_proxy # may be set externally as well
        self.dispatcher = None # the user which dispatches the messages to the webchat

        # init the empty channel
        self.channel = chan = ("!" + roomname).lower()
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

    def message(self, nick, msg, dest=None): # dest == None i.e. channel
        self._get_user(nick).message(dest or self.channel, msg, self.users.keys())

    def nickchange(self, old, new):
        user = _get_user(old)
        user.nick(new)

    def set_away(self, nick, away_status): # XXX not implemented
        pass

    def _get_user(self, nick):
        nick_sanitized = self.sanitize_nick(nick)
        IRC_ID = "%s!~%s@%s" % (nick_sanitized, 'webchatuser', 'somehost.invalid')
        user = self.users.setdefault(nick, GTChatUser(nick_sanitized, IRC_ID, self.server, self))
        return user

    def find_new_dispatcher(self, user):
        users = self.nicks.values()
        users.remove(user)
        if users:
            self.dispatcher = users[0]
        else:
            self.dispatcher = None


class GTChatUser(sirc.DummyUser):
    def __init__(self, nick, ID, server, incoming_proxy):
        sirc.DummyUser.__init__(self, nick, ID)
        self.incoming_proxy = incoming_proxy
        self.server = server
        self.init()

        if incoming_proxy.dispatcher is None:
            incoming_proxy.dispatcher = self

    def send(self, msg):
        m_user, m_cmd, m_self, m_message = (self.TranslateMessage(msg) + [""])[:4]
        m_cmd = m_cmd.lower()
        m_message = m_message[:-1]
        if m_cmd == 'privmsg':
            self.privmsg(m_user, m_self, msg, m_message)
        else:
            print self.data['nick'], "did not understand", msg

    def privmsg(self, user, dest, rawmsg, msg):
        print self, "got", rawmsg
        if self.incoming_proxy.dispatcher is self or dest == self.data['nick']:
            print "I have to dispatch this message to the webchat!"
            self.incoming_proxy.outgoing_proxy.message(msg, [None, dest][dest == self.data['nick']])

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
            if self.incoming_proxy.dispatcher is self:
                self.incoming_proxy.find_new_dispatcher(self)
            try:
                c = self.server.channels[chan]
            except KeyError:
                return
            c.remove(self, True, "")
            self.server.chanserv.event_part(self, c)
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

    def message(self, dest, msg, exempt_list):
        if dest[0] == '!':
            try:
                c = self.server.channels[dest]
            except KeyError:
                raise IRCException("No such channel")
            c.sendall(":%s PRIVMSG %s :%s\n" % (self.IRC_ID, c.name, msg), exempt_list)
        else:
            try:
                c = self.nicks[dest.lower()]
            except KeyError:
                raise IRCException("No such user")
            c.send(":%s PRIVMSG %s :%s\n" % (self.IRC_ID, dest, msg))

    def init(self):
        self.data['user'] = ("bridge", "server", "localhost", "")
        self.server.nicks[self.data['nick'].lower()] = self
        self.IRC_ID = "%s!~%s@%s" % (self.data['nick'], self.data['user'][0], "server")
        self.data['mode'] = ['i']
        self.server.nickserv.event_register(self)


import threading

class TestThread(threading.Thread):
    def __init__(self, conn):
        self.conn = conn
        conn.outgoing_proxy = self
        threading.Thread.__init__(self)

    def run(self):
        from time import sleep
        print "Simulating webchat"
        self.conn.join("rudi")
        sleep(10)
        self.conn.join("frauke")
        sleep(10)
        self.conn.join("herbert")
        self.conn.message("rudi", "hallo, ich bin rudi")
        sleep(3)
        self.conn.message("herbert", "hallo rudi")

    def message(self, txt, dest=None): # None -> current channel, otherwise nick
        """ This is a callback. """
        print "Sending to webchat (dest %s): " % dest, txt


def run_on_port(port):
    s = sirc.IRCServer((config.listen_ip, port), "chat.invalid")
    print "\nListening on %s:%d" % (config.listen_ip, port)

    conn = GTChatIncoming(s, config.room)
    t = TestThread(conn)
    t.start()
    s.run()


if __name__ == "__main__":
    import random
    port = random.randint(2000, 10000)#config.port
    run_on_port(port)

