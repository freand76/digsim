from components import Component, InputPort, SignalLevel


class Led(Component):
    def __init__(self, circuit, name="LED", callback=None):
        super().__init__(circuit, name)
        self._callback = callback
        self._in = InputPort(self)
        self.add_port("I", self._in)

    def set_callback(self, callback):
        self._callback = callback

    def update(self):
        if self._callback is not None:
            self._callback(self.name, self._in.level == SignalLevel.HIGH)
