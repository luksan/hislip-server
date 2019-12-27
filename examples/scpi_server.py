# -*- coding: utf-8 -*-
"""

@author: Lukas Sandström
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import re

from hislip_server import HislipServer, HislipClient


class SCPICommand(object):
    def __init__(self, cmd_str, query_fn=None, write_fn=None):
        self.cmd_str = cmd_str
        if query_fn is not None:
            self.query = query_fn
        if write_fn is not None:
            self.write = write_fn

    def query(self, *args):
        raise NotImplementedError()

    def write(self, *args):
        raise NotImplementedError()


class SCPIParser(object):
    def register_command(self, cmd):
        pass

    def parse(self, cmd):
        cmd, args = cmd.split(maxsplit=1)
        if cmd[-1] == b"?":
            o = self.find_cmd(cmd[:-1])
            o.query(*args)
        else:
            o = self.find_cmd(cmd)
            o.write(*args)

    def find_cmd(self, cmd):
        pass


class SCPIInstrument(object):
    class _CommandRegistry(dict):
        def __call__(self, *args, **kwargs):
            """
            Decorator for registering a method as SCPI command

            :param list of str *args: The SCPI command strings to be registered
            """
            def x(func):
                self.regster(func, args)
                return func
            return x

        def register(self, func, cmds):
            """

            :param func:
            :param list of str cmds:
            """
            for cmd in cmds:
                self._get_regex(cmd)

        def _get_regex(self, cmd):
            """
            Typical input: [SENSe1]:CORRection:EDELay1:DIELectric optional SENSe node
            CALCulate1:MARKer1 two indexes

            :param cmd:
            :return:
            """
            reg = []
            node_re = re.compile(r"^(?P<opt>\[(?=.*\]))?(?P<short>[*@]?[A-Z]+)(?P<tail>[a-z]*)(?P<index>1)?\]?$")
            nodes = cmd.split(":")
            for node in nodes:
                match = node_re.match(node)
                assert match is not None
                r = match.expand(r"(?\g<short>(?\g<tail>)?)")


    _cmd = _CommandRegistry()

    @_cmd("*IDN?")
    def idn_query(self):
        return "Vendor name,Instrument type,Instrument serial,FW rev."

class SCPIServer(HislipServer):
    def __init__(self, *args, **kwargs):
        super(SCPIServer, self).__init__(*args, **kwargs)
        self.scpi_parser = SCPIParser()


    def connection_request(self, client):
        """
        :param HislipClient client:
        :return:
        """
        # Check the sub address and other parameters, or send FatalError
        super(SCPIServer, self).connection_request(client)
        if client.instr_sub_addr != "hislip0":
            return

    def data_received(self, client, message):
        client.send_response()
        client.send_srq()


if __name__ == "__main__":
    pass
