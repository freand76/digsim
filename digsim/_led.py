from ._component import Component
from ._port import ComponentPort, PortDirection, SignalLevel


class Led(Component):
    def __init__(self, circuit, name="LED", callback=None):
        super().__init__(circuit, name)
        self._callback = callback
        self.add_port(ComponentPort(self, "I", PortDirection.IN))

    def set_callback(self, callback):
        self._callback = callback

    def update(self):
        if self._callback is not None:
            self._callback(
                self.circuit.time_ns, self.name, self.I.level == SignalLevel.HIGH
            )
