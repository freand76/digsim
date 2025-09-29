# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with 7-segment LED component"""

from .atoms import CallbackComponent, PortIn


class SevenSegment(CallbackComponent):
    """7-segment LED component class"""

    PORTLIST = ["A", "B", "C", "D", "E", "F", "G", "dot"]

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        for portname in self.PORTLIST:
            self.add_port(PortIn(self, portname))

    def segments(self):
        """Get the active segments"""
        segments = ""
        for portname in self.PORTLIST:
            if self.port(portname).value == 1:
                if portname == "dot":
                    segments += "."
                else:
                    segments += portname
        return segments
