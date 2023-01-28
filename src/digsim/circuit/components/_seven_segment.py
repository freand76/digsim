# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from .atoms import CallbackComponent, PortIn


class SevenSegment(CallbackComponent):

    PORTLIST = ["A", "B", "C", "D", "E", "F", "G", "dot"]

    def __init__(self, circuit, name="SevemSegment"):
        super().__init__(circuit, name)
        for portname in self.PORTLIST:
            self.add_port(PortIn(self, portname))

    def segments(self):
        segments = ""
        for portname in self.PORTLIST:
            if self.port(portname).value == 1:
                segments += portname
        return segments