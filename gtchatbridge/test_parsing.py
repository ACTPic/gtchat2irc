import sys

sys.path.append("..")

from gtchatbridge.gtchatclient import ChatParser


def test_message():
    test_data = '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">\n<html><body><font color="#00bb00"><b><a href="javascript:insertText(\'/msg xorEaxEax \')" onclick="insertText(\'/msg xorEaxEax \');return false;" style="color:#00bb00">xorEaxEax</a> (zu gwtest):</b> test</font></body></html>'
    ChatParser().process_string(test_data)

