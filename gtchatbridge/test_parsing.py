import sys

sys.path.append("..")

from gtchatbridge.gtchatclient import ChatParser


class GCITest(object):
    def __init__(self):
        self.data = []

    def message(self, nick, msg, dest=None): # dest == None i.e. channel
        self.data.append(("MESSAGE", nick, msg, dest))

    def set_away(self, nick, msg):
        self.data.append(("AWAY", nick, msg))

    def notice(self, msg):
        raise Exception("Unparsed text remains!")

    def nickchange(self, old, new):
        self.data.append(("NICKCHANGE", old, new))


def test_message():
    test_data = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">\n<html><body><font color="#00bb00"><b><a href="javascript:insertText(\'/msg xorEaxEax \')" onclick="insertText(\'/msg xorEaxEax \');return false;" style="color:#00bb00">xorEaxEax</a> (zu gwtest):</b> test</font></body></html>'
    cp = ChatParser(None, GCITest())
    cp.process_tree(cp.parse_string(test_data))

def test_notice():
    part_msg = """    <html><body><p>[ <b>Psychose-Chat:</b> &lt;&lt;&lt; franni paliko Psychose-Chati - dass mir aber die unregelm&#228;&#223;igen litauischen Verben bis zum n&#228;chsten Mal sitzen! ]<br/></p></body></html>"""
    join_msg = """<html><body><p>[ <b>Psychose-Chat:</b> &gt;&gt;&gt; biker strickt nebenher und tippt darum mit den F&#252;&#223;en. F&#252;reventuelle Tippfehler bitten wir um Verst&#228;ndnis. ]<br/></p></body></html>"""
    away_msg = """<html><head/><body><p>
[ <b>Psychose-Chat:</b> xorEaxEax ist jetzt weg: test ]<br/></p></body></html>"""
    away_end_msg = """<html><head/><body><p>
[ <b>Psychose-Chat:</b> xorEaxEax ist wieder da ]<br/><br/></p></body></html>"""
    change_nick_msg = """<html><head/><body><p>
[ <b>Psychose-Chat:</b> xorEaxFoo? xorEaxEax! ]<br/></p></body></html>"""
    double_msg = """<html><head/><body><p>
[ <b>Psychose-Chat:</b> xorEaxFoo? xorEaxEax! ]<br/></p><p>
[ <b>Psychose-Chat:</b> xorEaxFoo? xorEaxEax! ]<br/></p></body></html>"""
    gci = GCITest()
    cp = ChatParser(None, gci)
    cp.process_tree(cp.parse_string(join_msg))
    cp.process_tree(cp.parse_string(part_msg))
    cp.process_tree(cp.parse_string(away_msg))
    cp.process_tree(cp.parse_string(away_end_msg))
    cp.process_tree(cp.parse_string(change_nick_msg))
    cp.process_tree(cp.parse_string(double_msg))
    assert gci.data == [('AWAY', 'xorEaxEax', 'test'), ('AWAY', 'xorEaxEax', None),
            ('NICKCHANGE', 'xorEaxFoo', 'xorEaxEax'),
            ('NICKCHANGE', 'xorEaxFoo', 'xorEaxEax'),
            ('NICKCHANGE', 'xorEaxFoo', 'xorEaxEax')]


def test_urllist():
    d = ChatParser(None, None).process_userlist(userlist)
    T, F = True, False
    assert d == dict(birth=F, derwisch=F, Kim=T, martin78=F, Raphael=T, risperidon=F, Tim=F)

userlist = """<html>
<head>
<base href="http://www.psychose-chat.de/">
<link rel="stylesheet" href="style.css">
<title>Psychose-Chat</title>
<SCRIPT LANGUAGE="JavaScript" src="chat.js" type="text/javascript">
</SCRIPT>
<SCRIPT LANGUAGE="JavaScript">
	cgi="http://www.psychose-chat.de/cgi-bin/gtchat/chat.pl?id=446306494836794";
</SCRIPT>
</head>
<body id="body" marginheight=0 marginwidth=2 leftmargin=2 topmargin=0>

<table border=0 width=100% cellspacing=0 id="lines"><tr><td>  <!-- Netscape compatibility -->

<table border=0 width=100% cellspacing=1>

<tr>
	<th>
Raum Lobby<br>7 von 7 Benutzern
	</th>
</tr>
<tr id="table2">
	<td><table>
<tr><td nowrap><a href="javascript:insertText('@birth ')"><img src="images/at.gif" width="15" height="14" border=0 alt="@birth"></a> <a href="javascript:insertText('/msg birth ')"><img src="images/msg.gif" width="18" height="13" border=0 alt="/msg birth"></a> <a href="javascript:viewProfile('_hlyiwqb')">birth</a></td></tr>
<tr><td nowrap><a href="javascript:insertText('@derwisch ')"><img src="images/at.gif" width="15" height="14" border=0 alt="@derwisch"></a> <a href="javascript:insertText('/msg derwisch ')"><img src="images/msg.gif" width="18" height="13" border=0 alt="/msg derwisch"></a> <a href="javascript:viewProfile('_lt14wrnntl0a')">derwisch</a></td></tr>

<tr><td nowrap><a href="javascript:insertText('@Kim ')"><img src="images/at.gif" width="15" height="14" border=0 alt="@Kim"></a> <a href="javascript:insertText('/msg Kim ')"><img src="images/msg.gif" width="18" height="13" border=0 alt="/msg Kim"></a> <a href="javascript:viewProfile('_k11qwqznolzgxpfmmtyexsnmid3a')">(Kim)</a></td></tr>
<tr><td nowrap><a href="javascript:insertText('@martin78 ')"><img src="images/at.gif" width="15" height="14" border=0 alt="@martin78"></a> <a href="javascript:insertText('/msg martin78 ')"><img src="images/msg.gif" width="18" height="13" border=0 alt="/msg martin78"></a> <a href="javascript:viewProfile('_nlyeh0fno1nqd')">martin78</a></td></tr>
<tr><td nowrap><a href="javascript:insertText('@Raphael ')"><img src="images/at.gif" width="15" height="14" border=0 alt="@Raphael"></a> <a href="javascript:insertText('/msg Raphael ')"><img src="images/msg.gif" width="18" height="13" border=0 alt="/msg Raphael"></a> <a href="javascript:viewProfile('_slyahufmfd1a')">(Raphael)</a></td></tr>
<tr><td nowrap><a href="javascript:insertText('@risperidon ')"><img src="images/at.gif" width="15" height="14" border=0 alt="@risperidon"></a> <a href="javascript:insertText('/msg risperidon ')"><img src="images/msg.gif" width="18" height="13" border=0 alt="/msg risperidon"></a> <a href="javascript:viewProfile('_sl0ghyvmsl0iwxzn')">risperidon</a></td></tr>
<tr><td nowrap><a href="javascript:insertText('@Tim ')"><img src="images/at.gif" width="15" height="14" border=0 alt="@Tim"></a> <a href="javascript:insertText('/msg Tim ')"><img src="images/msg.gif" width="18" height="13" border=0 alt="/msg Tim"></a> <a href="javascript:viewProfile('_ut2sgyrnfd')">Tim</a></td></tr>

	</table></td>
</tr>
</table>

</td></tr></table>  <!-- Netscape compatibility -->
</body>
</html> 
"""
