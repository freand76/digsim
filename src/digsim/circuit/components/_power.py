# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from .atoms import Component, PortOut


class VDD(Component):
    def __init__(self, circuit, name="VDD"):
        super().__init__(circuit, name)
        self.add_port(PortOut(self, "O", delay_ns=0))

    def init(self):
        super().init()
        self.O.value = 1

    @property
    def wire(self):
        return self.o.wire

    @wire.setter
    def wire(self, port):
        self.O.wire = port


class GND(Component):
    def __init__(self, circuit, name="GND"):
        super().__init__(circuit, name)
        self.add_port(PortOut(self, "O", delay_ns=0))

    def init(self):
        super().init()
        self.O.value = 0

    @property
    def wire(self):
        return self.o.wire

    @wire.setter
    def wire(self, port):
        self.O.wire = port
