# Copyright (c) Fredrik Andersson, 2023
# All rights reserved

from .atoms import Component, OutputPort, SignalLevel, WireConnectionError


class VDD(Component):
    def __init__(self, circuit, name="VDD"):
        super().__init__(circuit, name)
        self.add_port(OutputPort(self, "O"))
        self.O.set_propagation_delay_ns(0)

    def init(self):
        super().init()
        self.O.level = SignalLevel.HIGH

    @property
    def wire(self):
        raise WireConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        self.O.wire = port


class GND(Component):
    def __init__(self, circuit, name="GND"):
        super().__init__(circuit, name)
        self.add_port(OutputPort(self, "O"))
        self.O.set_propagation_delay_ns(0)

    def init(self):
        super().init()
        self.O.level = SignalLevel.LOW

    @property
    def wire(self):
        raise WireConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        self.O.wire = port
