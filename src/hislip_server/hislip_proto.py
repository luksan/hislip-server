from collections import namedtuple
import struct
from typing import TypeAlias
import attr


class Connection:
    def receive_data(self) -> None:
        """Put received data in our input buffer."""
        pass

    def next_event(self):
        """Try to parse the input buffer and return a message, or NEED_MORE_DATA"""

    def async_connection(self):
        """Call this method when the async socket has been established."""
        pass


T_channel = TypeAlias(str)
CH_SYNC = "sync" # type: T_channel
CH_ASYNC = "async"  # type: T_channel

messages = {CH_ASYNC: {}, CH_SYNC: {}}

def message_type(msg_type: int, msg_channel: T_channel):
    """Decorator for Hislip message classes"""

    assert 0 <= msg_type <= 255
    assert not ( 26 <= msg_type <= 127 )  # Reserved for future std revision
    assert msg_channel in (CH_SYNC, CH_ASYNC)
    def dec(cls):
        messages[msg_channel][msg_type] = cls
        return cls
    return dec


def sync_message(msg_type: int):
    return message_type(msg_type=msg_type, msg_channel=CH_SYNC)


def async_message(msg_type: int):
    return message_type(msg_type=msg_type, msg_channel=CH_ASYNC)


@attr.s
class MessageHeader:
    _struct_hdr = struct.Struct("!2sBBIQ")
    # _msg_tuple = namedtuple("HiSLIP_message", ["prologue", "type", "ctrl_code", "param", "payload_len"])

    prologue = attr.ib(validator=lambda x: x == b"HS")
    type = attr.ib()
    ctrl_code = attr.ib()
    parameter = attr.ib()
    payload_len = attr.ib(validator=attr.validators.instance_of(int))

    def __len__(self):
        return self._struct_hdr.size

    @classmethod
    def from_bytes(cls, hdr_data: bytes):
        assert len(hdr_data) == cls._struct_hdr.size
        return cls(*cls._struct_hdr.unpack(hdr_data))

    def to_bytes(self):
        return self._struct_hdr.pack(self.prologue, self.type, self.ctrl_code, self.parameter, self.payload_len)

    @classmethod
    def make(cls, msg_type, ctrl_code, parameter, payload_len):
        return cls(b"HS", msg_type, ctrl_code, parameter, payload_len)


class HislipMessage:
    pass


@sync_message(msg_type=1)
class InitMessage(HislipMessage):
    pass
