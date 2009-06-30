#!/usr/bin/env python
"""
GT Chat to IRC Gateway

License: 3 clause BSD

In this file, the IRC server is instantiated and the
GTChat connection is established.

TODO:
    * Repair /whois in sirc and then add away msg parsing
    * Fix nick in sirc and add nick change parsing
    * Add /me support
"""

import sys


sys.path.append("..")

from gtchatbridge import sirc, config, gtchatclient


class GTChatOutgoingInterface(object):
    """ Interface """
    def message(self, txt, dest=None): # None -> current channel, otherwise nick
        pass

    def set_away(self, txt):
        pass

    def change_nick(self, newnick):
        pass


class GTChatIncoming(object):
    def __init__(self, server, roomname, outgoing_proxy=None):
        self.server = server
        self.roomname = roomname
        self.users = {} # nick -> GTChatUser()
        self.outgoing_proxy = outgoing_proxy # may be set externally as well
        self.dispatcher = None # the user which dispatches the messages to the webchat

        # init the empty channel
        self.channel = chan = ("&" + roomname).lower()
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

    def notice(self, msg):
        try:
            c = self.server.channels[self.channel]
        except KeyError:
            raise IRCException("No such channel")
        c.sendall(":%s NOTICE %s :%s\n" % (self.server.host, c.name, msg))

    def nickchange(self, old, new):
        user = self._get_user(old)
        user.nick(new, self.users.keys())

    def set_away(self, nick, away_status):
        self._get_user(nick).set_away(away_status)

    def _get_user(self, nick):
        nick_sanitized = self.sanitize_nick(nick)
        user = self.users.setdefault(nick, GTChatUser(nick_sanitized, "", self.server, self, self.channel))
        return user


class GTChatUser(sirc.DummyUser):
    def __init__(self, nick, ID, server, incoming_proxy, channel):
        sirc.DummyUser.__init__(self, nick, ID)
        self.incoming_proxy = incoming_proxy
        self.server = server
        self.channel = channel
        self.init()

        if incoming_proxy.dispatcher is None:
            incoming_proxy.dispatcher = self

    def send(self, msg):
        msgparts = self.TranslateMessage(msg.strip())
        m_cmd = msgparts[1]
        m_cmd = m_cmd.lower()
        if m_cmd == 'privmsg':
            m_user, _, m_self, m_message = msgparts
            self.privmsg(m_user, m_self, msg, m_message)
        elif m_cmd == 'nick':
            # does not work yet because sirc does not support it
            # yet
            m_user, _, newnick = msgparts # XXX we should check m_user here
            self.outgoing_proxy.change_nick(newnick)
        elif m_cmd == 'away':
            if len(msgparts) == 3:
                msg = msgparts[3]
            else:
                msg = None
            self.outgoing_proxy.set_away(msg)
        elif m_cmd in ('notice', 'join', 'mode', 'part'):
            pass # ignore
        else:
            print self.data['nick'], "did not understand", msg

    def privmsg(self, user, dest, rawmsg, msg):
        if self.incoming_proxy.dispatcher is self or dest == self.data['nick']:
            self.incoming_proxy.outgoing_proxy.message(msg, [None, dest][dest == self.data['nick']])

    def set_away(self, msg=None): # None -> reset away
        self.data['away'] = msg

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

    def nick(self, nick, exempt_list):
        self.server.lock.acquire_lock()
        try:
            oldnick = self.data['nick'].lower()
            old_id = self.IRC_ID
            del self.server.nicks[oldnick]
            self.data['nick'] = nick
            self.init()
            try:
                c = self.server.channels[self.channel]
            except KeyError:
                raise IRCException("No such channel")
            c.sendall(":%s NICK %s\n" % (old_id, nick), exempt_list)
        finally:
            self.server.lock.release_lock()

    def part(self, chan):
        self.server.lock.acquire_lock()
        try:
            if self.incoming_proxy.dispatcher is self:
                users = set(self.server.channels[self.incoming_proxy.channel].users.values())
                users &= set(self.incoming_proxy.users.values())
                users.remove(self)
                if users:
                    self.dispatcher = iter(users).next()
                else:
                    self.dispatcher = None
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
        if isinstance(msg, unicode):
            msg = msg.encode("latin-1")
        if dest is True:
            dest = self.server.clients.values()[0][0].data['nick'] # XXX choose correct client
        if dest[0] == '&':
            try:
                c = self.server.channels[dest]
            except KeyError:
                raise IRCException("No such channel")
            c.sendall(":%s PRIVMSG %s :%s\n" % (self.IRC_ID, c.name, msg), exempt_list)
        else:
            try:
                c = self.server.nicks[dest.lower()]
            except KeyError:
                raise IRCException("No such user")
            c.send(":%s PRIVMSG %s :%s\n" % (self.IRC_ID, dest, msg))

    def init(self):
        self.data['user'] = ("bridge", "server", "localhost", "")
        self.server.nicks[self.data['nick'].lower()] = self
        self.IRC_ID = "%s!~%s@%s" % (self.data['nick'], self.data['user'][0], "server")
        self.data['mode'] = ['i']


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
        self.conn.nickchange("herbert", "hannah")

    def message(self, txt, dest=None): # None -> current channel, otherwise nick
        """ This is a callback. """
        print "Sending to webchat (dest %s): " % dest, txt

    def set_away(self, txt):
        print "Setting away msg:", txt

    def change_nick(self, newnick):
        print "Changing nick to ", newnick


def generate_join_func(incoming):
    def join_user_to_channel(user):
        user.IRC_join((incoming.channel, ), True)
    return join_user_to_channel

def generate_away_func(outgoing):
    def event_away(user, msg):
        outgoing.set_away(msg)
    return event_away

def run_on_port(port):
    server = sirc.IRCServer((config.listen_ip, port), "chat.invalid")
    print "\nListening on %s:%d" % (config.listen_ip, port)

    conn = GTChatIncoming(server, config.room)
    server.event_join_finished = generate_join_func(conn)
    #    t = TestThread(conn)
    thread = gtchatclient.GTChatConnector(conn)
    conn.outgoing_proxy = thread
    server.event_user_away = generate_away_func(thread)
    thread.start()
    server.run()


if __name__ == "__main__":
    if config.port is None:
        import random
        port = random.randint(2000, 10000)
    else:
        port = config.port
    run_on_port(port)
    exit()  # kill gtchatclient thread too 

