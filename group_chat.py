#!/usr/bin/python
# ragsagar at gmail dot com
# code that connect gui with the functions
#

import socket
import gtk.glade
import sys
import pwd
import os
from threading import Thread


class ChatClient:
    def __init__(self, host, port, nickname):
        """ Initialize the gui components and socket variables """
        self.nickname = nickname
        self.host = host
        self.port = port
        self.done = False
        filename = "groupchat_gui.glade"
        try:
            builder = gtk.Builder()
            builder.add_from_file(filename)
        except:
            self.error_message("Failed to load UI file: %s" % filename)
            sys.exit(1)

        self.window = builder.get_object("mainWindow")
        self.chatEntry = builder.get_object("chatEntry")
        self.logWindow = builder.get_object("logWindow")
        self.buffer = gtk.TextBuffer(None)
        self.logWindow.set_buffer(self.buffer)

        builder.connect_signals(self)

    def connect_with_server(self):
        """ Logs into the server """
        self.socket = \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.input = self.socket.makefile('rb', 0)
        self.output = self.socket.makefile('wb', 0)
        authenticationDemand = self.input.readline()
        if not authenticationDemand.startswith("Who are you?"):
            print authenticationDemand
            raise Exception, "This doesn't seem to be correct server"
        self.output.write(self.nickname + '\r\n')
        response = self.input.readline().strip()
        if not response.startswith("Hi"):
            raise Exception, response
        print response
        #lists the chat room members
        self.output.write('/names\r\n')
        self.log("Current chat room members are: " + \
         self.input.readline().strip(), "black")
        self.manage_server_input()

    def manage_server_input(self):
        """Starts another thread to manage incoming from server"""
        propogateServerInput = self.PropogateServerInput(self,self.input)
        propogateServerInput.start()

        ##reads and print what got from server
        #inputText = True
        #while inputText:
            #inputText = self.input.readline()
            #if inputText:
                #self.log(inputText.strip())
        #propogateStandardInput.done = True

    class PropogateServerInput(Thread):
        """ This class runs as a seperate thread and pastes the
        incoming text from server to log window """

        def __init__(self, parent, input):
            Thread.__init__(self)
            self.setDaemon(True)
            self.input = input
            self.parent = parent

        def run(self):
            """Pastes the input from the server to log window """
            incomingText = True
            while incomingText:
                incomingText = self.input.readline().strip()
                if incomingText:
                    self.parent.log(incomingText,"black")
            self.parent.done = True
    def error_message(self, message):
        """ Displays the error dialog with message and logs it in shell """
        # log to terminal window
        print message
        # create an error message dialog and display modally to the user
        dialog = gtk.MessageDialog(None,
                                   gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                   gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, message)
        dialog.run()
        dialog.destroy()

    def log(self, message, color, enter="\n"):
        """Logs message to the Text view window"""
        message = message + enter
        buffer = self.buffer
        iter = buffer.get_end_iter()
        if color != "black":
            tag = buffer.create_tag()
            tag.set_property("foreground", color)
            self.buffer.insert_with_tags(buffer.get_end_iter(), message,
                    tag)
        else:
            self.buffer.insert(iter, message)
        mark = buffer.create_mark("end", buffer.get_end_iter(), False)
        self.logWindow.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)

    def main(self):
        self.window.show()
        self.connect_with_server()
        try:
            gtk.threads_init()
        except:
            self.error_message("gtk not compiled with threading support")
            sys.exit(1)
        gtk.threads_enter()
        gtk.main()
        gtk.threads_leave()

    # Signal Handlers

    def on_mainWindow_destroy(self, obj):
        """Handles destroy signal of window"""
        self.output.write("/quit\r\n")
        gtk.main_quit()
        sys.exit(1)

    def on_sendButton_clicked(self, obj):
        """Handles the clicked signal from button"""
        message = self.chatEntry.get_text()
        self.output.write(message + "\r\n")
        if message.split()[0] == "/quit":
            gtk.main_quit()
        self.chatEntry.set_text("")




if __name__ == '__main__':
    hostname, port, nickname = "localhost", 6001, pwd.getpwuid(os.getuid())[0]
    if len(sys.argv) > 1:
        hostname = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    if len(sys.argv) > 3:
        nickname = sys.argv[3]
    client = ChatClient(hostname,port,nickname)
    client.main()

