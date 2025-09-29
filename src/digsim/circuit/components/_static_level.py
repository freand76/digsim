# Copyright (c) Fredrik Andersson, 2023-2025
# All rights reserved

"""Module with the Static Logic components"""

from .atoms import Component, PortOutDelta


class VDD(Component):
    """VDD / Logic1 component class"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortOutDelta(self, "O", delay_ns=0))

    def default_state(self):
        self.O.value = 1


class GND(Component):
    """GND / Logic0 component class"""

    def __init__(self, circuit, name=None):
        super().__init__(circuit, name)
        self.add_port(PortOutDelta(self, "O", delay_ns=0))

    def default_state(self):
        self.O.value = 0
