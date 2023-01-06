# pylint: disable=no-member

from ._component import CallbackComponent
from ._port import ComponentPort, PortDirection, SignalLevel


class HexDigit(CallbackComponent):
    def __init__(self, circuit, name="LED", callback=None):
        super().__init__(circuit, name, callback)
        self.add_port(ComponentPort(self, "I0", PortDirection.IN))
        self.add_port(ComponentPort(self, "I1", PortDirection.IN))
        self.add_port(ComponentPort(self, "I2", PortDirection.IN))
        self.add_port(ComponentPort(self, "I3", PortDirection.IN))

    def value(self):
        if SignalLevel.UNKNOWN in [
            self.I0.level,
            self.I1.level,
            self.I2.level,
            self.I3.level,
        ]:
            return -1

        return (
            self.I3.intval << 3
            | self.I2.intval << 2
            | self.I1.intval << 1
            | self.I0.intval
        )
