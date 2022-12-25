from ._base import Component, ComponentPort, PortDirection, SignalLevel


class PushButton(Component):
    def __init__(self, circuit, name="PushButton", inverted=False):
        super().__init__(circuit, name)
        self._inverted = inverted
        self.add_port(ComponentPort(self, "O", PortDirection.OUT))

    def init(self):
        self.release()

    def push(self):
        if self._inverted:
            self.O.level = SignalLevel.LOW
        else:
            self.O.level = SignalLevel.HIGH

    def release(self):
        if self._inverted:
            self.O.level = SignalLevel.HIGH
        else:
            self.O.level = SignalLevel.LOW
