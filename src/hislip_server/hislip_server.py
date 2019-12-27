# -*- coding: utf-8 -*-
"""

@author: Lukas Sandström
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import struct
import threading
from cStringIO import StringIO

from pprint import pprint

import socket
try:
    import SocketServer as socketserver
except ImportError:
    import socketserver

from collections import namedtuple

from aenum import IntEnum


logger = logging.getLogger(__name__)


class HislipError(Exception):
    pass


class HislipProtocolError(HislipError):
    """Something went wrong on the wire"""
    pass


class HislipConnectionClosed(HislipError):
    pass


def repack(from_, to, *args):
    """
    Repacks data from one unpacked state to another.
    `struct.unpack(to, struct.pack(from_, *args))`

    :param from_: The struct which the *args will be packed into
    :param to: The target struct
    :param args: positional arguments
    :return: a tuple
    """
    return struct.unpack(to, struct.pack(from_, *args))


class Message(object):
    _type_check = None  # Used to check for the correct type in unpack when subclassing
    _subclasses = dict()  # Holds a reference for all defined subclasses msg_id => class

    @classmethod
    def message(cls, type_):
        """
        Decorator for subclasses
        """
        def x(subclass):
            subclass._type_check = type_
            cls._subclasses[type_] = subclass
            return subclass
        return x

    class Type(IntEnum):
        Initialize = 0
        InitializeResponse = 1
        FatalError = 2
        Error = 3
        AsyncLock = 4
        AsyncLockResponse = 5
        Data = 6
        DataEnd = 7
        DeviceClearComplete = 8
        DeviceClearAcknowledge = 9
        AsyncRemoteLocalControl = 10
        AsyncRemoteLocalResponse = 11
        Trigger = 12
        Interrupted = 13
        AsyncInterrupted = 14
        AsyncMaximumMessageSize = 15
        AsyncMaximumMessageSizeResponse = 16
        AsyncInitialize = 17
        AsyncInitializeResponse = 18
        AsyncDeviceClear = 19
        AsyncServiceRequest = 20
        AsyncStatusQuery = 21
        AsyncStatusResponse = 22
        AsyncDeviceClearAcknowledge = 23
        AsyncLockInfo = 24
        AsyncLockInfoResponse = 25

    prologue = b"HS"

    def __init__(self):
        self.type = self._type_check
        self.ctrl_code = 0
        self.param = 0
        self.payload = b""

    @classmethod
    def _copy(cls, msg):
        new = cls()
        new.type = msg.type
        new.ctrl_code = msg.ctrl_code
        new.param = msg.param
        new.payload = msg.payload
        return new

    def __str__(self):
        return "%s <%r> <%r> <%r> <%i> : <%r>" % \
               (self.prologue, self.type, self.ctrl_code, self.param, self.payload_len, self.payload[:50])

    @classmethod
    def parse(cls, fd):
        """
        A Message factory function, which reads a complete message from fd and returns an instance
        of the correct subclass, or Message() if there is no subclass available.

        :param fd: object implementing read()
        :return: A Message instance
        """
        tmp = cls()
        tmp.unpack(fd)
        if tmp.type not in cls._subclasses:
            return tmp
        return cls._subclasses[tmp.type]._copy(tmp)

    @property
    def payload_len(self):
        return len(self.payload)

    _struct_hdr = struct.Struct("!2sBBIQ")
    _msg_tuple = namedtuple("HiSLIP_message", ["prologue", "type", "ctrl_code", "param", "payload_len"])

    def pack(self):
        assert self.type is not None
        try:
            hdr = self._struct_hdr.pack(self.prologue, self.type, self.ctrl_code, self.param, self.payload_len)
        except Exception as e:
            logger.exception("struct.pack() failed.")
            raise
        return hdr + self.payload

    def unpack(self, fd):
        try:
            data = fd.read(self._struct_hdr.size)
        except socket.error as e:
            raise HislipConnectionClosed(e.message)
        if not len(data):
            raise HislipConnectionClosed("Short read. Connection closed.")
        msg = self._msg_tuple._make(self._struct_hdr.unpack_from(data))
        if msg.prologue != self.prologue:
            raise HislipProtocolError("Invalid message prologue")
        try:
            self.type = self.Type(msg.type)
        except ValueError:
            raise HislipProtocolError("Unknown message type (%i)" % msg.type)
        if self._type_check and self._type_check != self.type:
            raise HislipError("Unexpected message type (%i)" % self.type)
        self.ctrl_code = msg.ctrl_code
        self.param = msg.param
        self.payload = fd.read(msg.payload_len)
        if msg.payload_len != len(self.payload):
            raise HislipProtocolError("Invalid payload length, %i (header) != %i (actual)" %
                                      (msg.payload_len, len(self.payload)))


@Message.message(Message.Type.Initialize)
class MessageInitialize(Message):
    client_protocol_version = 0
    client_vendor_id = "ZZ"

    @property
    def sub_address(self):
        return str(self.payload)

    @sub_address.setter
    def sub_address(self, x):
        self.payload = str(x)

    @property
    def param(self):
        return repack("!H2s", "!I", self.client_protocol_version, self.client_vendor_id)[0]

    @param.setter
    def param(self, x):
        self.client_protocol_version, self.client_vendor_id = repack("!I", "!H2s", x)


@Message.message(Message.Type.InitializeResponse)
class MessageInitializeResponse(Message):
    server_protocol_version = struct.pack("!BB", 1, 0)
    session_id = None

    @property
    def overlap_mode(self):
        return self.ctrl_code & 1

    @overlap_mode.setter
    def overlap_mode(self, x):
        if x:
            self.ctrl_code = 1
        else:
            self.ctrl_code = 0

    @property
    def param(self):
        return repack("!HH", "!I", self.server_protocol_version, self.session_id)[0]

    @param.setter
    def param(self, x):
        self.server_protocol_version, self.session_id = repack("!I", "!HH", x)


@Message.message(Message.Type.AsyncInitialize)
class MessageAsyncInitialize(Message):
    @property
    def session_id(self):
        return self.param

    @session_id.setter
    def session_id(self, x):
        self.param = int(x)


@Message.message(Message.Type.AsyncInitializeResponse)
class MessageAsyncInitializeResponse(Message):
    @property
    def server_vendor_id(self):
        return repack("!I", "!xx2s", self.param)[0]

    @server_vendor_id.setter
    def server_vendor_id(self, x):
        assert len(str(x)) == 2
        self.param = repack("!xx2s", "!I", str(x))[0]


@Message.message(Message.Type.AsyncMaximumMessageSize)
class MessageAsyncMaximumMessageSize(Message):
    @property
    def max_size(self):
        assert self.payload_len == 8
        return struct.unpack("!Q", self.payload)

    @max_size.setter
    def max_size(self, x):
        self.payload = struct.pack("!Q", x)


@Message.message(Message.Type.AsyncMaximumMessageSizeResponse)
class MessageAsyncMaximumMessageSizeResponse(MessageAsyncMaximumMessageSize):
    pass


@Message.message(Message.Type.AsyncLock)
class MessageAsyncLock(Message):
    @property
    def request(self):
        return self.ctrl_code & 1

    @property
    def release(self):
        return not self.ctrl_code & 1

    @property
    def timeout(self):
        assert self.request  # The timeout parameter is only sent when requesting the lock
        return self.param


@Message.message(Message.Type.AsyncLockResponse)
class MessageAsyncLockResponse(Message):
    pass


@Message.message(Message.Type.AsyncLockInfoResponse)
class MessageAsyncLockInfoResponse(Message):
    @property
    def exclusive_lock_granted(self):
        return self.ctrl_code & 1

    @exclusive_lock_granted.setter
    def exclusive_lock_granted(self, x):
        if x:
            self.ctrl_code = 1
        else:
            self.ctrl_code = 0

    @property
    def lock_count(self):
        return self.param

    @lock_count.setter
    def lock_count(self, x):
        self.param = int(x)


@Message.message(Message.Type.Data)
class MessageData(Message):
    @property
    def RMT(self):
        return self.ctrl_code & 1

    @RMT.setter
    def RMT(self, x):
        if x:
            self.ctrl_code = 1
        else:
            self.ctrl_code = 0

    @property
    def message_id(self):
        return self.param

    @message_id.setter
    def message_id(self, x):
        self.param = int(x)


@Message.message(Message.Type.AsyncStatusQuery)
class MessageAsyncStatusQuery(MessageData):
    pass


@Message.message(Message.Type.AsyncStatusResponse)
class MessageAsyncStatusResponse(MessageData):
    @property
    def status(self):
        return self.ctrl_code

    @status.setter
    def status(self, x):
        self.ctrl_code = x


@Message.message(Message.Type.DataEnd)
class MessageDataEnd(MessageData):
    pass


@Message.message(Message.Type.AsyncDeviceClearAcknowledge)
class MessageAsyncDeviceClearAcknowledge(Message):
    @property
    def overlap_mode(self):
        return self.ctrl_code & 1

    @overlap_mode.setter
    def overlap_mode(self, x):
        if x:
            self.ctrl_code = 1
        else:
            self.ctrl_code = 0


@Message.message(Message.Type.DeviceClearComplete)
class MessageDeviceClearComplete(MessageAsyncDeviceClearAcknowledge):
    pass


@Message.message(Message.Type.DeviceClearAcknowledge)
class MessageDeviceClearAcknowledge(MessageAsyncDeviceClearAcknowledge):
    pass


@Message.message(Message.Type.Trigger)
class MessageTrigger(MessageData):
    pass


class HislipClient(object):
    def __init__(self):
        self.instr_sub_addr = None
        self.overlap_mode = None
        self.session_id = None

        #private
        self.lock = threading.RLock()

        self.sync_handler = None
        self.async_handler = None

        self.max_message_size = None
        self.sync_buffer = StringIO()
        self.message_id = 0xffffff00
        self.MAV = False  # Message available for client. See HiSLIP 4.14.1
        self.RMT_expected = False

    def get_stb(self):
        if self.MAV:
            return 0x10
        return 0x00


class HislipHandler(socketserver.StreamRequestHandler, object):
    class _MsgHandler(dict):
        def __call__(self, msg_type):  # Decorator for registering handler methods
            def x(func):
                self[msg_type] = func
                return func
            return x

    msg_handler = _MsgHandler()

    def __init__(self, request, client_address, server):
        """
        :param socket.Socket request:
        :param client_address:
        :param HislipServer server:
        """
        socketserver.BaseRequestHandler.__init__(self, request, client_address, server)
        self.server = server
        self.client = None
        self.sync_conn = None
        self.session_id = None

    def send_msg(self, message):
        logger.debug(" resp: %s", message)
        if message.type == Message.Type.Data or message.type == Message.Type.DataEnd:
            with self.client.lock:  # HiSLIP 4.14.1
                self.client.MAV = True
        self.wfile.write(message.pack())

    def init_connection(self):
        init = Message.parse(self.rfile)
        if init.type == Message.Type.Initialize:
            self.sync_init(init)
        elif init.type == Message.Type.AsyncInitialize:
            self.async_init(init)
        else:
            raise HislipProtocolError("Unexpected message at connection init, %r" % init)

    def sync_init(self, msg):
        """
        :param MessageInitialize msg:
        """
        # Send message to subclass
        # check protocol version

        with self.server.client_lock:
            self.client, session_id = self.server.new_client(), self.server.new_session_id()
        with self.client.lock:
            self.client.session_id = session_id
            self.client.sync_handler = self
            self.client.instr_sub_addr = msg.payload
        self.sync_conn = True

        logger.info("Connection from %r to %s", self.client_address, msg.payload)

        error = self.server.connection_request(self.client)
        if error is not None:
            self.send_msg(error)
            self.server.client_disconnect(self.client)
            raise error

        response = MessageInitializeResponse()
        response.overlap_mode = self.server.overlap_mode
        response.session_id = self.session_id
        self.send_msg(response)
        # Setup of sync channel complete, wait for connection of async channel

    def async_init(self, msg):
        """
        :param MessageAsyncInitialize msg:
        """
        self.session_id = msg.session_id
        try:
            self.client = self.server.get_client(msg.session_id)
        except KeyError:
            raise HislipProtocolError("AsyncInitialize with unknown session id.")
        with self.client.lock:
            if self.client.async_handler is not None:
                raise HislipProtocolError("AsyncInitialize with already initialized session.")
            self.client.async_handler = self

        self.sync_conn = False
        response = MessageAsyncInitializeResponse()
        response.server_vendor_id = self.server.vendor_id
        self.send_msg(response)

    @msg_handler(Message.Type.AsyncDeviceClear)
    def async_device_clear(self, msg):  # HiSLIP 4.12
        # FIXME: stub
        response = MessageAsyncDeviceClearAcknowledge()
        response.overlap_mode = self.server.overlap_mode
        self.send_msg(response)

    @msg_handler(Message.Type.DeviceClearComplete)
    def device_clear(self, msg):  # HiSLIP 4.12
        # FIXME: stub
        overlap = msg.overlap_mode
        response = MessageDeviceClearAcknowledge()
        response.overlap_mode = self.server.overlap_mode
        self.send_msg(response)

    @msg_handler(Message.Type.AsyncLock)
    def async_lock(self, msg):
        # FIXME: stub
        response = MessageAsyncLockResponse()
        response.ctrl_code = 1
        self.send_msg(response)

    @msg_handler(Message.Type.AsyncLockInfo)
    def async_lock_info(self, msg):
        # FIXME: locking stub
        response = MessageAsyncLockInfoResponse()
        response.exclusive_lock_granted = True
        response.lock_count = 1
        self.send_msg(response)

    @msg_handler(Message.Type.AsyncStatusQuery)
    def async_status_query(self, msg):
        response = MessageAsyncStatusResponse()
        with self.client.lock:
            if msg.RMT:
                self.client.MAV = False
            response.status = self.client.get_stb()
        self.send_msg(response)

    @msg_handler(Message.Type.AsyncMaximumMessageSize)
    def max_size_message(self, msg):
        """
        :param MessageAsyncMaximumMessageSize msg:
        """
        with self.client.lock:
            self.client.max_message_size = msg.max_size
            response = MessageAsyncMaximumMessageSizeResponse()
            response.max_size = int(self.server.max_message_size)
            self.send_msg(response)

    @msg_handler(Message.Type.Data)
    def sync_data(self, msg):
        """
        :param MessageData msg:
        """
        with self.client.lock:
            if msg.RMT:
                self.client.MAV = False
            self.client.sync_buffer.write(msg.payload)

    @msg_handler(Message.Type.DataEnd)
    def sync_data_end(self, msg):
        with self.client.lock:
            if msg.RMT:
                self.client.MAV = False
            self.client.sync_buffer.write(msg.payload)
            self.client.message_id = msg.message_id
            self.client.sync_buffer.seek(0)
            data = self.client.sync_buffer.read()
            logger.debug("DataEnd: %r" % data)
            if len(data) > 2 and data[-2] == "?":
                response = MessageDataEnd()
                response.message_id = self.client.message_id
                response.payload = b"RS,123,456,798\n"
                self.send_msg(response)

            # FIXME: pass data to application
            self.client.sync_buffer = StringIO()  # Clear the buffer

    @msg_handler(Message.Type.Trigger)
    def trigger(self, msg):
        with self.client.lock:
            self.client.message_id = msg.message_id
            if msg.RMT:
                self.client.MAV = False

    def handle(self):
        self.init_connection()
        if self.sync_conn:
            prf = " sync: %s"
        else:
            prf = "async: %s"
        while True:
            try:
                msg = Message.parse(self.rfile)
            except HislipConnectionClosed as e:
                logger.info("Connection closed, %r", self.client_address)
                self.server.client_disconnect(self.client)
                break

            logger.debug(prf, str(msg))
            if msg.type in self.msg_handler:
                self.msg_handler[msg.type](self, msg)
            else:
                logger.warning("No handler for this message")


class HislipServer(socketserver.ThreadingTCPServer, object):
    def __init__(self, *args, **kwargs):
        super(HislipServer, self).__init__(*args, **kwargs)

        self.vendor_id = b"\x52\x53"  # R & S
        self.max_message_size = 500e6
        self.overlap_mode = False

        self.allow_reuse_address = True

        self.client_lock = threading.RLock()
        self.clients = dict()  # session id => Client()
        self._last_session_id = 0

    def read_stb(self):
        # Override this in a subclass
        return 0

    def new_session_id(self):
        self._last_session_id += 1
        return self._last_session_id

    def new_client(self):
        return HislipClient()

    def get_client(self, session_id):
        """
        :param session_id:
        :rtype: HislipClient
        """
        with self.client_lock:
            return self.clients[session_id]

    def connection_request(self, client):
        """
        This method can be used to reject incomming connections by returning a MessageFatalError

        :param HislipClient client:
        :return: None or MessageFatalError
        """

        with self.client_lock:
            self.clients[client.session_id] = client

    def client_disconnect(self, client):
        with self.client_lock:
            try:
                client = self.clients.pop(client.session_id)
            except KeyError:
                return

        with client.lock:
            try:
                if client.sync_handler is not None:
                    client.sync_handler.request.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            try:
                if client.async_handler is not None:
                    client.async_handler.request.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass


def _main():
    import sys
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    hislip_server = HislipServer(("localhost", 4880), HislipHandler)
    server_thread = threading.Thread(target=hislip_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    raw_input("Enter to end")


import stacktracer

if __name__ == "__main__":
    stacktracer.trace_start("trace.html")
    _main()
