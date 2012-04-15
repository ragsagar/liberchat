#!/usr/bin/python
# librechat client made for librebox project
# ragsagar at gmail dot com
#

import gtk
import sys
import pwd
import os
import socket
from threading import Thread

GLADEFILE_LISTWINDOW = "listwindow.glade"
GLADEFILE_CHATWINDOW = "chatwindow.glade"

class ChatClient:

    def __init__(self,hostname,port,nickname):
        self.hostname = hostname
        self.port = port
        self.nickname = nickname
        self.nicklist = []
        self.chatterList = {}
        #initializing gui components
        try:
            builder = gtk.Builder()
            builder.add_from_file(GLADEFILE_LISTWINDOW)
        except:
            self.error_message("Failed to load UI file: " +
                    GLADEFILE_LISTWINDOW)
            sys.exit(1)

        self.listWindow = builder.get_object("window1")
        self.liststore = builder.get_object("liststore")
        self.treeview = builder.get_object("treeview1")
        self.chatButton = builder.get_object("chatButton")
        self.builder = builder

        builder.connect_signals(self)

    def connect_with_server(self):
        """ Connects with the server and fetches the list of available
        nicknames from there using the /names command"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.hostname, self.port))
        self.input = self.socket.makefile("rb", 0)
        self.output = self.socket.makefile("wb", 0)
        authenticationDemand = self.input.readline()
        if not authenticationDemand.startswith("Who are you"):
            raise Exception, "Incorrect server"
        self.output.write(self.nickname + "\r\n")
        response = self.input.readline().strip()
        if not response.startswith("Hi"):
            raise Exception, response
        self.update_liststore()
        self.manage_server_incoming()

    def manage_server_incoming(self):
        """Manages the server incoming as a seperate thread """
        propogateServerIncoming = self.PropogateServerIncoming(self,
                self.input)
        propogateServerIncoming.start()

    class PropogateServerIncoming(Thread):
        """ This class runs as a separate thread and manages the incoming
        text from the server """

        def __init__(self, pObj, input):
            Thread.__init__(self)
            self.setDaemon(True)
            self.input = input
            self.pObj = pObj

        def run(self):
            incomingText = True
            while incomingText:
                incomingText = self.input.readline().strip()
                if incomingText.endswith("has quit") or \
                incomingText.endswith("joined the chat."):
                    self.pObj.update_liststore()
                elif incomingText.startswith("!privmsg"):
                    nick, msg = incomingText.split(" ", 1)[1].split(" ", 1)
                    if not nick in self.pObj.chatterList:
                        self.pObj.chatterList[nick] = \
                                self.pObj.ChatWindow(self.pObj, nick, self.pObj.output)
                    self.pObj.chatterList[nick].insert_into_logWindow(msg)
                elif incomingText.startswith("!") and \
                "is now known as" in incomingText:
                    old_nick = incomingText.split()[0]
                    new_nick = incomingText.split()[-1]
                    if old_nick == self.nickname:
                        self.nickname = new_nick
                    self.update_liststore()





    def update_liststore(self):
        """Populates the list of nicknames in liststore"""
        self.output.write("/names\r\n")
        self.nicklist = self.input.readline().strip().split(",")
        try:
            self.nicklist.remove(self.nickname)
        except ValueError:
            pass
        print self.nicklist
        self.liststore.clear()
        for nick in self.nicklist:
            self.liststore.append([nick])

    def main(self):
        self.connect_with_server()
        self.update_liststore()
        self.listWindow.show()
        gtk.threads_init()
        gtk.threads_enter()
        gtk.main()
        gtk.threads_leave()

    # listWindow Signal Handlers

    def on_chatButton_clicked(self, obj):
        """ Starts private with the selected person """
        selection = self.treeview.get_selection()
        model, iter = selection.get_selected()
        selected_nick, = self.liststore.get(iter, 0)
        if selected_nick not in self.chatterList:
            self.chatterList[selected_nick] = self.ChatWindow(self, selected_nick,
                    self.output)


    def on_window1_destroyed(self, obj):
        """ Quits everything """
        self.output.write("/quit\r\n")
        gtk.main_quit()
        sys.exit(1)

    class ChatWindow():

        def __init__(self, pObj, selectedNick, output):
            """Initialize the chatWindow components """
            try:
                builder = gtk.Builder()
                builder.add_from_file(GLADEFILE_CHATWINDOW)
            except:
                raise "Failed to load UI from file ", GLADEFILE_CHATWINDOW
                sys.exit(1)
            builder.connect_signals(self)
            self.pObj = pObj
            self.selectedNick = selectedNick
            self.output = output
            self.chatWindow = builder.get_object("chatWindow")
            self.logWindow = builder.get_object("textview1")
            self.sendButton = builder.get_object("sendButton")
            self.chatEntry = builder.get_object("chatEntry")
            self.buffer = gtk.TextBuffer(None)
            self.logWindow.set_buffer(self.buffer)
            self.chatWindow.show()

        def insert_into_logWindow(self, message, color="black"):
            """ Inserts the message into the logWindow """
            message = message + "\n"
            buffer = self.buffer
            iter = buffer.get_end_iter()
            if color != "black":
                tag = buffer.create_tag()
                tag.set_property("foreground", color)
                self.buffer.insert_with_tags(buffer.get_end_iter(), message, \
                    tag)
            else:
                self.buffer.insert(iter, message)
            mark = buffer.create_mark("end", buffer.get_end_iter(), False)
            self.logWindow.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)


        def on_sendButton_clicked(self, obj):
            """ The typed text is fetched from chatEntry and sent to
            the server """
            typedText = self.chatEntry.get_text()
            if typedText:
                if not typedText.startswith("/"):
                    # send it as a private message to particular user
                    self.output.write("/privmsg " + self.selectedNick + " " + typedText + "\r\n")
                    self.insert_into_logWindow("<%s> %s" % (self.pObj.nickname,
                    typedText))
                else:
                    # it is a command, so directly send it to the server
                    self.output.write(typedText+"\r\n")
            self.chatEntry.set_text("")

        def on_chatWindow_destroyed(self, obj):
            """ Hide the chatWindow and delete the object from
            chatterList so that the chatWindow will be created
            again for another privmsg from the same user. """
            del self.pObj.chatterList[self.selectedNick]
            self.chatWindow.destroy()


if __name__ == '__main__':
    hostname, port = "localhost", 6001
    nickname = pwd.getpwuid(os.getuid())[0]
    if len(sys.argv) > 1:
        hostname = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    if len(sys.argv) > 3:
        nickname = sys.argv[3]
    client = ChatClient(hostname, port, nickname)
    client.main()



