#!/usr/bin/python
# ragsagar at gmail dot com
# Hippo chat written for liberbox project


import SocketServer
import re
import socket

class ChatError(Exception):
    "Exception thrown when client gives bad input to the server"
    pass

class ChatServer(SocketServer.ThreadingTCPServer):
    "Server class"

    def __init__(self, server_address, RequestHandlerClass):
        SocketServer.ThreadingTCPServer.__init__(self, server_address, \
                RequestHandlerClass)
        self.users = {}

class RequestHandler(SocketServer.StreamRequestHandler):
    "Handles the connecting, chatting and commands"
    NICKNAME = re.compile('^[A-Za-z0-9_-]+$')

    def handle(self):
        """ Handles connection """
        # Logging in
        self.nickname = None
        self.privateMessage("Who are you?")
        nickname = self._readline()
        done = False
        try:
            self.nickCommand(nickname)
            self.privateMessage("Hi %s,Welcome to Server" % nickname)
            self.broadcast("%s has joined the chat." % nickname, False)
        except ChatError, error:
            self.privateMessage(error.args[0])
            done = True
        except socket.error:
            done = True

        # Chatting session

        while not done:
            try:
                done = self.processInput()
            except ChatError, error:
                self.privateMessage(str(error))
            except socket.error, e:
                done = True

    def finish(self):
        """Automatically called when handle() is done"""
        if self.nickname:
            message = '%s has quit' % self.nickname
            if hasattr(self, 'partingWords'):
                message = '%s has quit: %s' % (self.nickname,
                        self.partingWords)
            self.broadcast(message, False)
            if self.server.users.get(self.nickname):
                del(self.server.users[self.nickname])
        self.request.shutdown(2)
        self.request.close()

    def processInput(self):
        """ Reads from the socket input """
        done = False
        line = self._readline()
        command, arg = self._parseCommand(line)
        if command:
            done = command(arg)
        else:
            line = "<%s> %s\n" % (self.nickname, line)
            self.broadcast(line)
        return done

    def nickCommand(self, nickname):
        """Command to change nickname"""
        if not nickname:
            raise ChatError, "No nickname provided"
        if not self.NICKNAME.match(nickname):
            raise ChatError, "Invalid nickname %s" % nickname
        if nickname == self.nickname:
            raise ChatError, "You are already %s." % nickname
        if self.server.users.get(nickname, None):
            raise ChatError, "%s already exists" % nickname
        old_nickname = None
        if self.nickname:
            old_nickname = self.nickname
            del(self.server.users[self.nickname])
        self.server.users[nickname] = self.wfile
        self.nickname = nickname
        if old_nickname:
            self.broadcast("!%s is now known as %s" % \
                    (old_nickname,self.nickname))

    def quitCommand(self, partingWords):
        """Implementation of /quit command"""
        if partingWords:
            self.partingWords = partingWords
        # Returning true will make the user disconnected
        return True

    def namesCommand(self, ignored):
        """Returns list of users in chat room"""
        self.privateMessage(','.join(self.server.users.keys()))

    def privmsgCommand(self, nicknameAndMsg):
        """ Send private message to a user """
        print "Private message called, ", nicknameAndMsg
        if not ' ' in nicknameAndMsg:
            raise ChatError("No message specified.")
        nickname, msg = nicknameAndMsg.split(' ', 1)
        if nickname == self.nickname:
            raise ChatError("Sending private message to yourself")
        user = self.server.users.get(nickname)
        if not user:
            raise ChatError("No such user: %s" % nickname)
        msg = "<%s> %s" % (self.nickname, msg)
        msg = "!privmsg %s %s" % (self.nickname, msg)
        user.write(self._ensureNewline(msg))


    def broadcast(self, message, include_me=True):
        """Sends message to everyone in the chat room"""
        message = self._ensureNewline(message)
        for user, output in self.server.users.items():
            if include_me or user != self.nickname:
                output.write(message)

    def privateMessage(self, message):
        """Sends a private message to this user"""
        self.wfile.write(self._ensureNewline(message))

    def _readline(self):
        """Reads a line"""
        return self.rfile.readline().strip()

    def _ensureNewline(self, string):
        """Makes sure the given string ends in a newline"""
        if string and string[-1] != '\n':
            string += '\r\n'
        return string

    def _parseCommand(self, input):
        """Tries to parse given input as command"""
        commandMethod, arg = None, None
        if input and input[0] == '/':
            if len(input) < 2:
                raise ChatError, "Invalid command: '%s'" % input
            commandAndarg = input[1:].split(' ',1)
            if len(commandAndarg) == 2:
                command, arg = commandAndarg
            else:
                command, = commandAndarg
            commandMethod = getattr(self, command + "Command", None)
            if not commandMethod:
                raise ChatError, "No such command: '%s'" % command
        return commandMethod, arg

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print "Usage: %s [hostname] [port]" % sys.argv[0]
        sys.exit(1)
    hostname = sys.argv[1]
    port = int(sys.argv[2])
    ChatServer((hostname, port),RequestHandler).serve_forever()


