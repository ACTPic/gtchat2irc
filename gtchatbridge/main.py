"""
GT Chat to IRC Gateway

License: 3 clause BSD

In this file, the IRC server is instantiated and the
GTChat connection is established.
"""

def run_on_port(port):
    s = IRCServer(('0.0.0.0', port), "localhost")
    print "\nListening on port %d" % port
    s.run()

if __name__ == "__main__":
    run_on_port(6667)

