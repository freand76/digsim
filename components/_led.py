from components import Component, InputPort, SignalLevel


class Led(Component):
    def __init__(self, circuit, name="LED", callback=None):
        super().__init__(circuit, name)
        self._callback = callback
        self._in = InputPort(self)
        self.add_port("I", self._in)

    def set_callback(self, callback):
        self._callback = callback

    @property
    def state(self):
        return "1" if self._in.level == SignalLevel.HIGH else "0"

    def update(self):
        if self._callback is not None:
            self._callback(
                self.circuit.time_ns, self.name, self._in.level == SignalLevel.HIGH
            )
