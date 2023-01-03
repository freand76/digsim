# pylint: disable=no-member

from ._component import CallbackComponent
from ._port import ComponentPort, PortDirection, SignalLevel


class Led(CallbackComponent):
    def __init__(self, circuit, name="LED", callback=None):
        super().__init__(circuit, name, callback)
        self.add_port(ComponentPort(self, "I", PortDirection.IN))

    @property
    def active(self):
        return self.I.level == SignalLevel.HIGH
