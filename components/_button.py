from ._base import Component, OutputPort, SignalLevel


class PushButton(Component):
    def __init__(self, circuit, name="PushButton", inverted=False):
        super().__init__(circuit, name)
        self._inverted = inverted
        self._out = OutputPort(self, propagation_delay_ns=0)
        self.add_port("O", self._out)

    def init(self):
        self.release()

    def push(self):
        if self._inverted:
            self._out.level = SignalLevel.LOW
        else:
            self._out.level = SignalLevel.HIGH

    def release(self):
        if self._inverted:
            self._out.level = SignalLevel.HIGH
        else:
            self._out.level = SignalLevel.LOW
