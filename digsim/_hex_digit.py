# pylint: disable=no-member

from ._component import CallbackComponent
from ._port import ComponentPort, PortDirection


class HexDigit(CallbackComponent):
    def __init__(self, circuit, name="LED", callback=None):
        super().__init__(circuit, name, callback)
        self.add_port(ComponentPort(self, "I0", PortDirection.IN))
        self.add_port(ComponentPort(self, "I1", PortDirection.IN))
        self.add_port(ComponentPort(self, "I2", PortDirection.IN))
        self.add_port(ComponentPort(self, "I3", PortDirection.IN))

    def value(self):
        return (
            self.I3.intval << 3
            | self.I2.intval << 2
            | self.I1.intval << 1
            | self.I0.intval
        )
