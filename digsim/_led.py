from ._base import Component, ComponentPort, PortDirection, SignalLevel


class Led(Component):
    def __init__(self, circuit, name="LED", callback=None):
        super().__init__(circuit, name)
        self._callback = callback
        self.add_port(ComponentPort(self, "I", PortDirection.IN))

    def set_callback(self, callback):
        self._callback = callback

    @property
    def state(self):
        return "1" if self.I.level == SignalLevel.HIGH else "0"

    def update(self):
        if self._callback is not None:
            self._callback(
                self.circuit.time_ns, self.name, self.I.level == SignalLevel.HIGH
            )
