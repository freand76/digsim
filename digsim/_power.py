# pylint: disable=no-member

from ._component import Component
from ._port import ComponentPort, PortDirection, SignalLevel


class VDD(Component):
    def __init__(self, circuit, name="VDD"):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "O", PortDirection.OUT))

    def init(self):
        super().init()
        self.O.level = SignalLevel.HIGH

    @property
    def wire(self):
        raise ConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        self.O.wire = port


class GND(Component):
    def __init__(self, circuit, name="GND"):
        super().__init__(circuit, name)
        self.add_port(ComponentPort(self, "O", PortDirection.OUT))

    def init(self):
        super().init()
        self.O.level = SignalLevel.LOW

    @property
    def wire(self):
        raise ConnectionError("Cannot get a wire")

    @wire.setter
    def wire(self, port):
        self.O.wire = port
